import os
import sys
import time
import math
import random
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from sentence_transformers import SentenceTransformer
import chromadb
from google import genai
from google.genai import types

from .config import (
    RAW_DATA_DIR,
    VECTORDB_DIR,
    CHROMA_COLLECTION_NAME,
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
    Lightweight, dependency-free BM25 implementation for lexical keyword search
    across chunks, enabling high-precision hybrid retrieval for statutes and section codes.
    """
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = 0
        self.avg_dl = 0.0
        self.doc_lengths: List[int] = []
        self.doc_tokens: List[List[str]] = []
        self.doc_ids: List[str] = []
        self.idf: Dict[str, float] = {}

    def _tokenize(self, text: str) -> List[str]:
        # Simple, robust alphanumeric tokenizer
        import re
        return [w.lower() for w in re.findall(r'\b\w+\b', text) if len(w) > 1]

    def fit(self, ids: List[str], documents: List[str]):
        self.doc_ids = ids
        self.doc_tokens = [self._tokenize(doc) for doc in documents]
        self.corpus_size = len(self.doc_tokens)
        self.doc_lengths = [len(doc) for doc in self.doc_tokens]
        self.avg_dl = sum(self.doc_lengths) / self.corpus_size if self.corpus_size > 0 else 1.0

        # Compute document frequencies
        df: Dict[str, int] = {}
        for tokens in self.doc_tokens:
            for term in set(tokens):
                df[term] = df.get(term, 0) + 1

        # Calculate BM25 IDF with smoothing
        for term, freq in df.items():
            self.idf[term] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        if self.corpus_size == 0:
            return []
        query_tokens = self._tokenize(query)
        scores: List[float] = [0.0] * self.corpus_size

        for term in query_tokens:
            if term not in self.idf:
                continue
            term_idf = self.idf[term]
            for doc_idx, tokens in enumerate(self.doc_tokens):
                tf = tokens.count(term)
                if tf == 0:
                    continue
                dl = self.doc_lengths[doc_idx]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (dl / self.avg_dl))
                scores[doc_idx] += term_idf * (numerator / denominator)

        # Pair scores with IDs and sort descending
        ranked = sorted(zip(self.doc_ids, scores), key=lambda x: x[1], reverse=True)
        return [(doc_id, score) for doc_id, score in ranked[:top_k] if score > 0]


class RAGPipeline:
    """
    Unified RAG orchestration service:
    - Lazy model loading & caching
    - Hybrid dense + BM25 keyword retrieval with Reciprocal Rank Fusion
    - Dynamic query routing
    - Corrective RAG (Self-reflection and query reformulation)
    - Resilient LLM calling with exponential backoff & jitter
    """
    _instance: Optional["RAGPipeline"] = None

    def __init__(self):
        self._embedder: Optional[SentenceTransformer] = None
        self._chroma_client: Optional[chromadb.PersistentClient] = None
        self._collection = None
        self._llm_client: Optional[genai.Client] = None
        self._bm25_index: Optional[BM25Index] = None
        self._indexed_docs_cache: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_instance(cls) -> "RAGPipeline":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

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

        models_to_try = [model, "gemini-3.8-flash", "gemini-3.8-flash-lite", "gemini-flash-latest", "gemini-2.5-flash", "gemini-3.5-flash"]
        # Deduplicate preserving order
        unique_models = list(dict.fromkeys(models_to_try))

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
                    is_rate_limit = "429" in err_str or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower()
                    is_server_error = "500" in err_str or "503" in err_str or "overloaded" in err_str.lower()
                    is_network_timeout = "timeout" in err_str.lower() or "connect" in err_str.lower() or "10060" in err_str or "10054" in err_str or "connection" in err_str.lower()

                    if (is_rate_limit or is_server_error or is_network_timeout) and attempt < max_retries - 1:
                        # Exponential backoff with jitter: 2s, 4s, 8s + random 0-1s
                        sleep_seconds = (2 ** (attempt + 1)) + random.uniform(0.5, 1.5)
                        logger.warning(f"Gemini API transient failure ({current_model}: {err_str[:80]}...). Retrying in {sleep_seconds:.1f}s...")
                        time.sleep(sleep_seconds)
                        continue
                    # Break attempt loop to try next model fallback if rate limit persists
                    break
        raise last_error or RuntimeError("LLM generation failed across all models.")

    def get_available_documents(self) -> List[str]:
        """Returns filenames of regulatory PDFs present on disk or in the database."""
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

    def retrieve(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        routing_filter: Optional[Dict[str, Any]] = None,
        use_hybrid: bool = True
    ) -> Tuple[List[str], List[Dict[str, Any]], List[float]]:
        """
        Retrieves relevant chunks using dense vector similarity or Reciprocal Rank Fusion (hybrid).
        """
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
        top_k: int = DEFAULT_TOP_K
    ) -> Dict[str, Any]:
        """
        Executes complete RAG pipeline synchronously.
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
        docs, metas, dists = self.retrieve(active_query, top_k=top_k, routing_filter=routing_filter, use_hybrid=use_hybrid)

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
                new_docs, new_metas, _ = self.retrieve(active_query, top_k=top_k, routing_filter=routing_filter, use_hybrid=use_hybrid)
                if new_docs:
                    docs, metas = new_docs, new_metas
                    context_prompt, cited_sources = self.format_context_prompt(active_query, docs, metas)

        # 5. Answer Generation
        answer = self.call_llm(context_prompt, system=SYSTEM_PROMPT, model=GENERATION_MODEL_NAME)

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
            "latency_sec": round(time.time() - start_time, 2)
        }
