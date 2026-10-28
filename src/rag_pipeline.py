import os
import sys
import time
import math
import random
import logging
import queue
import threading
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import numpy as np
try:
    import torch
    torch.set_num_threads(1)
except Exception:
    pass
from sentence_transformers import SentenceTransformer
import chromadb
from google import genai
from google.genai import types

try:
    import psycopg
    from pgvector.psycopg import register_vector
    HAS_PSYCOPG = True
except ImportError:
    HAS_PSYCOPG = False

from .config import (
    RAW_DATA_DIR,
    VECTORDB_DIR,
    CHROMA_COLLECTION_NAME,
    DATABASE_URL,
    EMBEDDING_MODEL_NAME,
    GENERATION_MODEL_NAME,
    FAST_MODEL_NAME,
    DEFAULT_TOP_K,
    SYSTEM_PROMPT,
)

logger = logging.getLogger("LexFinRAG")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class BM25Index:
    """
    High-performance inverted-index BM25 implementation for lexical keyword search
    across chunks, enabling sub-millisecond hybrid retrieval for statutes and section codes.
    """
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = 0
        self.avg_dl = 0.0
        self.doc_lengths: List[int] = []
        self.doc_ids: List[str] = []
        self.idf: Dict[str, float] = {}
        # Inverted index: term -> list of (doc_idx, tf)
        self.inverted_index: Dict[str, List[Tuple[int, int]]] = {}

    def _tokenize(self, text: str) -> List[str]:
        # Simple, robust alphanumeric tokenizer
        import re
        return [w.lower() for w in re.findall(r'\b\w+\b', text) if len(w) > 1]

    def fit(self, ids: List[str], documents: List[str]):
        from collections import Counter, defaultdict
        self.doc_ids = ids
        self.corpus_size = len(documents)
        self.doc_lengths = []
        
        term_postings = defaultdict(list)
        df: Dict[str, int] = defaultdict(int)

        for doc_idx, doc in enumerate(documents):
            tokens = self._tokenize(doc)
            self.doc_lengths.append(len(tokens))
            counts = Counter(tokens)
            for term, tf in counts.items():
                term_postings[term].append((doc_idx, tf))
                df[term] += 1

        self.avg_dl = sum(self.doc_lengths) / self.corpus_size if self.corpus_size > 0 else 1.0
        self.inverted_index = dict(term_postings)

        # Calculate BM25 IDF with smoothing
        for term, freq in df.items():
            self.idf[term] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        if self.corpus_size == 0:
            return []
        query_tokens = set(self._tokenize(query))
        scores: Dict[int, float] = {}

        for term in query_tokens:
            if term not in self.idf:
                continue
            term_idf = self.idf[term]
            postings = self.inverted_index.get(term, [])
            for doc_idx, tf in postings:
                dl = self.doc_lengths[doc_idx]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (dl / self.avg_dl))
                scores[doc_idx] = scores.get(doc_idx, 0.0) + (term_idf * (numerator / denominator))

        if not scores:
            return []

        # Sort top scores
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [(self.doc_ids[doc_idx], score) for doc_idx, score in ranked if score > 0]


class NeonConnectionPool:
    """
    Thread-safe connection pool for Neon Serverless Postgres with pgvector.
    Maintains a pool of connections with automatic reconnection and liveness
    validation for serverless scale-to-zero environments.
    """
    def __init__(self, dsn: str, max_connections: int = 5, timeout: float = 30.0):
        self.dsn = dsn
        self.max_connections = max_connections
        self.timeout = timeout
        self._pool: queue.Queue = queue.Queue(maxsize=max_connections)
        self._lock = threading.Lock()
        self._current_size = 0

    def _create_connection(self):
        conn = psycopg.connect(self.dsn, autocommit=True)
        register_vector(conn)
        return conn

    def getconn(self):
        # Try getting an idle connection from the pool without waiting
        try:
            conn = self._pool.get_nowait()
            if not conn.closed:
                try:
                    conn.execute("SELECT 1;")
                    return conn
                except Exception:
                    try:
                        conn.close()
                    except Exception:
                        pass
        except queue.Empty:
            pass

        # Create new connection if below capacity
        with self._lock:
            if self._current_size < self.max_connections:
                try:
                    conn = self._create_connection()
                    self._current_size += 1
                    return conn
                except Exception as e:
                    logger.error(f"Failed to create new Neon connection: {e}")
                    raise

        # Wait for an available connection if at capacity
        conn = self._pool.get(timeout=self.timeout)
        if conn.closed:
            conn = self._create_connection()
        return conn

    def putconn(self, conn):
        if conn and not conn.closed:
            try:
                self._pool.put_nowait(conn)
            except queue.Full:
                try:
                    conn.close()
                except Exception:
                    pass
                with self._lock:
                    self._current_size = max(0, self._current_size - 1)
        else:
            with self._lock:
                self._current_size = max(0, self._current_size - 1)

    @contextmanager
    def connection(self):
        conn = self.getconn()
        try:
            yield conn
        finally:
            self.putconn(conn)

    def closeall(self):
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
            except Exception:
                pass
        with self._lock:
            self._current_size = 0


class RAGPipeline:
    """
    Unified RAG orchestration service:
    - Lazy model loading & caching
    - Hybrid dense + BM25 keyword retrieval with Reciprocal Rank Fusion
    - Dynamic query routing
    - Corrective RAG (Self-reflection and query reformulation)
    - Resilient LLM calling with exponential backoff & jitter
    - Thread-safe Neon Serverless Postgres connection pooling
    """
    _instance: Optional["RAGPipeline"] = None

    def __init__(self):
        self._embedder: Optional[SentenceTransformer] = None
        self._chroma_client: Optional[chromadb.PersistentClient] = None
        self._collection = None
        self._llm_client: Optional[genai.Client] = None
        self._bm25_index: Optional[BM25Index] = None
        self._indexed_docs_cache: Dict[str, Dict[str, Any]] = {}
        self._pg_pool: Optional[NeonConnectionPool] = None

    @classmethod
    def get_instance(cls) -> "RAGPipeline":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def is_neon_enabled(self) -> bool:
        return bool(DATABASE_URL and HAS_PSYCOPG)

    def _get_pool(self) -> Optional[NeonConnectionPool]:
        if not self.is_neon_enabled:
            return None
        if self._pg_pool is None:
            try:
                self._pg_pool = NeonConnectionPool(DATABASE_URL)
                logger.info("Initialized Neon Serverless Postgres connection pool.")
            except Exception as e:
                logger.error(f"Failed to initialize Neon connection pool: {e}")
                return None
        return self._pg_pool

    @contextmanager
    def pg_connection(self):
        """Thread-safe context manager to checkout and return a connection from the pool."""
        pool = self._get_pool()
        if pool is None:
            yield None
            return
        with pool.connection() as conn:
            yield conn

    def _get_pg_conn(self):
        """Backwards compatibility helper for warm-up and ping."""
        pool = self._get_pool()
        if pool is None:
            return None
        try:
            conn = pool.getconn()
            pool.putconn(conn)
            return conn
        except Exception as e:
            logger.error(f"Failed to get connection from Neon pool: {e}")
            return None

    @property
    def embedder(self) -> SentenceTransformer:
        if self._embedder is None:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
            self._embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
        return self._embedder

    @property
    def chroma_collection(self):
        if self._collection is None:
            if not VECTORDB_DIR.exists():
                raise FileNotFoundError(f"ChromaDB directory not found at {VECTORDB_DIR}. Ingest documents first.")
            logger.info(f"Connecting to ChromaDB at: {VECTORDB_DIR}")
            self._chroma_client = chromadb.PersistentClient(path=str(VECTORDB_DIR))
            self._collection = self._chroma_client.get_collection(name=CHROMA_COLLECTION_NAME)
            logger.info(f"Loaded collection '{CHROMA_COLLECTION_NAME}' ({self._collection.count()} chunks)")
        return self._collection

    @property
    def llm_client(self) -> genai.Client:
        if self._llm_client is None:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable is missing. Set it in .env.")
            self._llm_client = genai.Client(api_key=api_key)
        return self._llm_client

    def _init_bm25_if_needed(self):
        """Builds in-memory BM25 index from ChromaDB document records for hybrid search."""
        if self._bm25_index is None:
            try:
                coll = self.chroma_collection
                records = coll.get(include=["documents", "metadatas"])
                ids = records.get("ids", [])
                docs = records.get("documents", [])
                metadatas = records.get("metadatas", [])
                
                self._indexed_docs_cache = {
                    ids[i]: {"text": docs[i], "metadata": metadatas[i]}
                    for i in range(len(ids))
                }
                
                bm25 = BM25Index()
                bm25.fit(ids, docs)
                self._bm25_index = bm25
                logger.info(f"Built BM25 hybrid index with {len(ids)} documents.")
            except Exception as e:
                logger.warning(f"Could not build BM25 index: {e}. Falling back to pure dense search.")

    def call_llm(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: str = GENERATION_MODEL_NAME,
        max_retries: int = 3
    ) -> str:
        """
        Calls Gemini with exponential backoff and jitter for rate-limiting resilience.
        """
        client = self.llm_client
        config = types.GenerateContentConfig()
        if system:
            config.system_instruction = system

        models_to_try = [
            model,
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-flash-latest",
            "gemini-flash-lite-latest",
            "gemini-2.5-pro",
        ]
        # Deduplicate preserving order
        unique_models = [m for m in dict.fromkeys(models_to_try) if m]

        last_error = None
        for current_model in unique_models:
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model=current_model,
                        contents=prompt,
                        config=config
                    )
                    return response.text.strip()
                except Exception as e:
                    last_error = e
                    err_str = str(e)
                    is_not_found = "404" in err_str or "not found" in err_str.lower()
                    if is_not_found:
                        logger.warning(f"Model {current_model} unavailable (404 Not Found). Trying fallback...")
                        break

                    is_rate_limit = "429" in err_str or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower()
                    if is_rate_limit:
                        logger.warning(f"Model {current_model} quota reached (429 Resource Exhausted). Instantly switching to next model...")
                        break

                    is_server_error = "500" in err_str or "503" in err_str or "overloaded" in err_str.lower()
                    is_network_timeout = "timeout" in err_str.lower() or "connect" in err_str.lower() or "10060" in err_str or "10054" in err_str or "connection" in err_str.lower()

                    if (is_server_error or is_network_timeout) and attempt < max_retries - 1:
                        sleep_seconds = 1.0 + random.uniform(0.2, 0.8)
                        logger.warning(f"Gemini API transient network failure ({current_model}: {err_str[:80]}...). Retrying in {sleep_seconds:.1f}s...")
                        time.sleep(sleep_seconds)
                        continue
                    break
        raise last_error or RuntimeError("LLM generation failed across all models.")

    def get_available_documents(self) -> List[str]:
        """Returns filenames of regulatory PDFs present in Neon Postgres, disk, or ChromaDB."""
        if self.is_neon_enabled:
            try:
                with self.pg_connection() as conn:
                    if conn:
                        with conn.cursor() as cur:
                            cur.execute("SELECT filename FROM documents WHERE status = 'ACTIVE' ORDER BY filename;")
                            rows = cur.fetchall()
                            if rows:
                                return [r[0] for r in rows]
            except Exception as e:
                logger.warning(f"Failed to fetch documents from Neon: {e}")

        available_files: List[str] = []
        if RAW_DATA_DIR.exists():
            available_files = [f.name for f in RAW_DATA_DIR.glob("*.pdf")]

        if not available_files:
            try:
                results = self.chroma_collection.get(include=["metadatas"])
                metadatas = results.get("metadatas", [])
                unique_sources = set()
                for meta in metadatas:
                    if meta and "source_filename" in meta:
                        unique_sources.add(meta["source_filename"])
                available_files = sorted(list(unique_sources))
            except Exception:
                pass
        return sorted(available_files)

    def route_query(self, query: str) -> Tuple[Optional[Dict[str, Any]], Optional[List[str]]]:
        """
        Dynamically classifies query against the available document catalog.
        """
        available_pdfs = self.get_available_documents()
        if not available_pdfs:
            return None, None

        doc_list_prompt = "\n".join([f"- {pdf}" for pdf in available_pdfs])
        routing_prompt = (
            f"You are a regulatory document router.\n"
            f"Question: '{query}'\n\n"
            f"Available documents:\n{doc_list_prompt}\n\n"
            "Task: Identify which document(s) this question is specifically about.\n"
            "Rules:\n"
            "- Reply ONLY with the exact filename(s) comma-separated if specific to certain documents.\n"
            "- If the question could span multiple documents or is general/unclear, reply with 'ALL'.\n"
            "- Do not include any explanations, markdown, or commentary."
        )

        try:
            route_text = self.call_llm(routing_prompt, model=FAST_MODEL_NAME)
            logger.info(f"Query routing decision: '{route_text}'")
            if "ALL" not in route_text.upper():
                selected = [f for f in available_pdfs if f.lower() in route_text.lower()]
                if selected:
                    if len(selected) == 1:
                        return {"source_filename": selected[0]}, selected
                    else:
                        return {"source_filename": {"$in": selected}}, selected
        except Exception as e:
            logger.warning(f"Query routing skipped due to error: {e}")

        return None, None

    def rewrite_conversational_query(self, current_question: str, history: List[Dict[str, str]]) -> str:
        """
        Rewrites conversational follow-up questions into standalone queries.
        """
        if not history:
            return current_question

        recent = history[-6:]
        history_str = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in recent])
        prompt = (
            "Given the following conversation history, rewrite the user's latest question into a "
            "standalone, fully descriptive search query that contains all necessary entities and context.\n\n"
            f"History:\n{history_str}\n\n"
            f"Latest Question: {current_question}\n\n"
            "Output ONLY the rewritten standalone question. No quotes or explanation."
        )
        try:
            rewritten = self.call_llm(prompt, model=FAST_MODEL_NAME)
            return rewritten if rewritten else current_question
        except Exception as e:
            logger.warning(f"Query rewrite skipped due to error: {e}")
            return current_question

    def retrieve_neon(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        routing_filter: Optional[Dict[str, Any]] = None,
        use_hybrid: bool = True,
        institution_type: Optional[str] = None
    ) -> Tuple[List[str], List[Dict[str, Any]], List[float]]:
        """
        Executes single-statement hybrid retrieval on Neon Postgres:
        - Relational filters (status, institution tier, document routing)
        - Dense vector cosine similarity via HNSW index (pgvector)
        - Lexical full-text search via GIN tsvector index
        - Relational metadata joins (documents + sections + applicability)
        """
        if not self.is_neon_enabled:
            return [], [], []

        query_emb = np.array(self.embedder.encode(query), dtype=np.float32)

        where_clauses = ["d.status = 'ACTIVE'"]
        where_params: List[Any] = []

        # 1. Routing filter (by document filename)
        if routing_filter and "source_filename" in routing_filter:
            target = routing_filter["source_filename"]
            if isinstance(target, str):
                where_clauses.append("c.source_filename = %s")
                where_params.append(target)
            elif isinstance(target, dict) and "$in" in target:
                where_clauses.append("c.source_filename = ANY(%s)")
                where_params.append(list(target["$in"]))

        # 2. Relational institution tier filter
        if institution_type:
            where_clauses.append("a.institution_type = %s")
            where_params.append(institution_type)

        where_sql = " AND ".join(where_clauses)

        # Hybrid scoring combining dense cosine similarity (70%) and full-text keyword rank (30%)
        if use_hybrid:
            order_sql = "((0.7 * (1 - (c.embedding <=> %s))) + (0.3 * LEAST(ts_rank(c.tsv_tokens, plainto_tsquery('english', %s)), 1.0))) DESC"
            order_params = [query_emb, query]
        else:
            order_sql = "(c.embedding <=> %s) ASC"
            order_params = [query_emb]

        select_params = [query_emb]
        all_params = select_params + where_params + order_params + [top_k]

        sql = f"""
        SELECT 
            c.chunk_text,
            c.source_filename,
            c.page_number,
            c.section_title,
            d.title AS doc_title,
            d.category AS doc_category,
            1 - (c.embedding <=> %s) AS cosine_sim
        FROM document_chunks c
        JOIN documents d ON c.document_id = d.id
        LEFT JOIN document_applicability a ON d.id = a.document_id
        WHERE {where_sql}
        ORDER BY {order_sql}
        LIMIT %s;
        """

        with self.pg_connection() as conn:
            if not conn:
                return [], [], []
            with conn.cursor() as cur:
                cur.execute(sql, all_params)
                rows = cur.fetchall()

        docs = []
        metas = []
        dists = []
        for r in rows:
            text, fname, page, section, title, category, sim = r
            docs.append(text)
            metas.append({
                "source_filename": fname,
                "page_number": str(page),
                "section_title": section or "Unknown",
                "document_title": title,
                "document_category": category,
            })
            dists.append(1.0 - float(sim))

        return docs, metas, dists

    def retrieve(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        routing_filter: Optional[Dict[str, Any]] = None,
        use_hybrid: bool = True,
        institution_type: Optional[str] = None
    ) -> Tuple[List[str], List[Dict[str, Any]], List[float]]:
        """
        Retrieves relevant chunks using Neon Postgres (pgvector) if available,
        or ChromaDB + inverted-index BM25 fallback.
        """
        if self.is_neon_enabled:
            try:
                neon_docs, neon_metas, neon_dists = self.retrieve_neon(
                    query=query,
                    top_k=top_k,
                    routing_filter=routing_filter,
                    use_hybrid=use_hybrid,
                    institution_type=institution_type
                )
                if neon_docs:
                    return neon_docs, neon_metas, neon_dists
            except Exception as e:
                logger.warning(f"Neon retrieval failed: {e}. Falling back to local ChromaDB.")

        query_embedding = self.embedder.encode(query).tolist()
        
        dense_kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k * 2, 20),
            "include": ["metadatas", "documents", "distances"]
        }
        if routing_filter:
            dense_kwargs["where"] = routing_filter

        coll = self.chroma_collection
        dense_results = coll.query(**dense_kwargs)

        if not dense_results["ids"] or not dense_results["ids"][0]:
            return [], [], []

        dense_ids = dense_results["ids"][0]
        dense_docs = dense_results["documents"][0]
        dense_metas = dense_results["metadatas"][0]
        dense_dists = dense_results["distances"][0]

        if not use_hybrid:
            return dense_docs[:top_k], dense_metas[:top_k], dense_dists[:top_k]

        # Hybrid Reciprocal Rank Fusion (RRF) with BM25
        self._init_bm25_if_needed()
        if not self._bm25_index:
            return dense_docs[:top_k], dense_metas[:top_k], dense_dists[:top_k]

        bm25_results = self._bm25_index.search(query, top_k=top_k * 2)
        
        # Apply routing filter to BM25 if active
        if routing_filter and "source_filename" in routing_filter:
            target = routing_filter["source_filename"]
            if isinstance(target, str):
                bm25_results = [
                    (doc_id, score) for doc_id, score in bm25_results
                    if self._indexed_docs_cache.get(doc_id, {}).get("metadata", {}).get("source_filename") == target
                ]
            elif isinstance(target, dict) and "$in" in target:
                allowed = set(target["$in"])
                bm25_results = [
                    (doc_id, score) for doc_id, score in bm25_results
                    if self._indexed_docs_cache.get(doc_id, {}).get("metadata", {}).get("source_filename") in allowed
                ]

        # RRF scoring (Constant k = 60)
        rrf_constant = 60
        scores: Dict[str, float] = {}

        for rank, doc_id in enumerate(dense_ids):
            scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (rrf_constant + rank + 1))

        for rank, (doc_id, _) in enumerate(bm25_results):
            scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (rrf_constant + rank + 1))

        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]

        final_docs = []
        final_metas = []
        final_scores = []

        # Map back to documents and metadata
        dense_id_map = {dense_ids[i]: (dense_docs[i], dense_metas[i], dense_dists[i]) for i in range(len(dense_ids))}

        for doc_id in sorted_ids:
            if doc_id in dense_id_map:
                doc, meta, dist = dense_id_map[doc_id]
                final_docs.append(doc)
                final_metas.append(meta)
                final_scores.append(dist)
            elif doc_id in self._indexed_docs_cache:
                item = self._indexed_docs_cache[doc_id]
                final_docs.append(item["text"])
                final_metas.append(item["metadata"])
                final_scores.append(0.5)  # neutral distance for BM25-primary matches

        return final_docs, final_metas, final_scores

    def format_context_prompt(self, question: str, documents: List[str], metadatas: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
        """Formats retrieved chunks with clear metadata boundaries for citation generation."""
        context_parts = []
        sources = []

        for i, text in enumerate(documents):
            meta = metadatas[i]
            source = meta.get("source_filename", "Unknown Document")
            page = meta.get("page_number", "Unknown")
            section = meta.get("section_title") or "General Section"

            source_id = f"{source} (Page {page})"
            if source_id not in sources:
                sources.append(source_id)

            part = (
                f"--- EXCERPT {i+1} ---\n"
                f"DOCUMENT: {source}\n"
                f"PAGE: {page}\n"
                f"SECTION: {section}\n"
                f"CONTENT:\n{text}\n"
            )
            context_parts.append(part)

        context_str = "\n".join(context_parts)
        prompt = (
            f"Here is the verified context extracted from official regulatory documents:\n\n"
            f"<context>\n{context_str}\n</context>\n\n"
            f"Question: {question}\n\n"
            "Instructions:\n"
            "- Synthesize an accurate, grounded answer strictly based on the excerpts above.\n"
            "- Explicitly cite the document name, page, and section for each regulatory rule mentioned."
        )
        return prompt, sources

    def reflect_and_reformulate(self, query: str, context_prompt: str, original_query: str) -> Optional[str]:
        """
        Corrective RAG: Assesses context sufficiency. If insufficient, returns a reformulated query.
        """
        eval_prompt = (
            f"Question: '{query}'\n\n"
            f"Retrieved Documents:\n{context_prompt}\n\n"
            "Task: Are the retrieved documents sufficient to provide a factual, accurate answer to the question?\n"
            "Reply strictly with 'YES' or 'NO' followed by a brief reason."
        )

        try:
            check_text = self.call_llm(eval_prompt, model=FAST_MODEL_NAME)
            logger.info(f"Corrective reflection result: {check_text}")
            if check_text.upper().startswith("NO"):
                reformulate_prompt = (
                    f"The user asked: '{original_query}'. The initial search returned insufficient results.\n"
                    "Rewrite this query into a single, highly descriptive keyword search query "
                    "tailored for legal/financial regulatory texts.\n"
                    "Output ONLY the new search query string without quotes or explanation."
                )
                reformulated = self.call_llm(reformulate_prompt, model=FAST_MODEL_NAME)
                logger.info(f"Reformulated query: '{reformulated}'")
                return reformulated
        except Exception as e:
            logger.warning(f"Corrective RAG step failed: {e}")
        return None

    def execute_rag(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
        corrective: bool = False,
        routing: bool = False,
        use_hybrid: bool = True,
        top_k: int = DEFAULT_TOP_K,
        institution_type: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes complete RAG pipeline synchronously with Neon Postgres or local fallback.
        """
        start_time = time.time()
        active_query = question
        rewritten_query = None
        routed_to = None
        reformulated_query = None

        # 1. Conversational Query Rewriting
        if history:
            rewritten_query = self.rewrite_conversational_query(question, history)
            active_query = rewritten_query

        # 2. Query Routing
        routing_filter = None
        if routing:
            routing_filter, routed_to = self.route_query(active_query)

        # 3. Retrieval
        docs, metas, dists = self.retrieve(
            active_query,
            top_k=top_k,
            routing_filter=routing_filter,
            use_hybrid=use_hybrid,
            institution_type=institution_type
        )

        if not docs:
            return {
                "answer": "I could not find any relevant information in the documents to answer your question.",
                "sources": [],
                "rewritten_query": rewritten_query,
                "routed_to": routed_to,
                "reformulated_query": None,
                "latency_sec": round(time.time() - start_time, 2)
            }

        context_prompt, cited_sources = self.format_context_prompt(active_query, docs, metas)

        # 4. Corrective RAG (Self-Reflection)
        if corrective:
            new_query = self.reflect_and_reformulate(active_query, context_prompt, question)
            if new_query and new_query.strip():
                reformulated_query = new_query.strip()
                active_query = reformulated_query
                new_docs, new_metas, _ = self.retrieve(
                    active_query,
                    top_k=top_k,
                    routing_filter=routing_filter,
                    use_hybrid=use_hybrid,
                    institution_type=institution_type
                )
                if new_docs:
                    docs, metas = new_docs, new_metas
                    context_prompt, cited_sources = self.format_context_prompt(active_query, docs, metas)

        # 5. Answer Generation
        answer = self.call_llm(context_prompt, system=SYSTEM_PROMPT, model=GENERATION_MODEL_NAME)
        elapsed_latency = round(time.time() - start_time, 2)

        # Record compliance audit log if Neon is available
        if self.is_neon_enabled:
            try:
                with self.pg_connection() as conn:
                    if conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                            INSERT INTO chat_audit_logs (session_id, user_query, assistant_answer, routed_to, latency_sec)
                            VALUES (%s, %s, %s, %s, %s);
                            """, (session_id or "web-session", question, answer, routed_to, elapsed_latency))
            except Exception as e:
                logger.warning(f"Could not record audit log to Neon: {e}")

        # Build structured sources for UI
        detailed_sources = []
        for i, doc in enumerate(docs):
            m = metas[i]
            detailed_sources.append({
                "source_filename": m.get("source_filename", "Unknown"),
                "page_number": str(m.get("page_number", "Unknown")),
                "section_title": m.get("section_title") or "Unknown",
                "text": doc
            })

        return {
            "answer": answer,
            "sources": detailed_sources,
            "cited_source_labels": cited_sources,
            "rewritten_query": rewritten_query,
            "routed_to": routed_to,
            "reformulated_query": reformulated_query,
            "latency_sec": elapsed_latency
        }
