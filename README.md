# ComplyGH: Agentic RAG for Bank of Ghana Regulatory Compliance

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16.4-black.svg)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/Neon-pgvector-00e599.svg)](https://neon.tech/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**ComplyGH** is an enterprise-grade **Agentic Retrieval-Augmented Generation (RAG)** platform engineered specifically for Ghanaian financial and banking regulations. It automates compliance intelligence across Bank of Ghana (BOG) directives, parliamentary statutes, cybersecurity guidelines, anti-money laundering frameworks, and payment systems rules. 

Unlike generic conversational bots, ComplyGH delivers strictly grounded, verifiable citations down to the exact statutory instrument, page number, and section title, backed by automated evaluation and continuous audit trails.

---

## System Architecture

```mermaid
graph TD
    UserQuery([User Regulatory Query]) --> Rewriter[1. Conversational Query Rewriter\nResolves context, pronouns & legal entities]
    Rewriter --> Router[2. Dynamic Document Router\nFilters search space by regulatory scope]
    
    subgraph Storage & Retrieval Layer
        Router --> DualEngine{Neon Postgres Available?}
        DualEngine -- Yes --> Neon[Neon Serverless PostgreSQL\nDense pgvector <=> + GIN tsvector ts_rank]
        DualEngine -- Fallback --> LocalChroma[ChromaDB + In-Memory BM25\nReciprocal Rank Fusion RRF k=60]
    end

    Neon --> Reflector[3. Corrective Self-Reflection CRAG\nEvaluates relevance & context sufficiency]
    LocalChroma --> Reflector
    
    Reflector -- Sufficient Context --> Generator[4. Grounded Answer Synthesizer\nGemini 3.8 Flash + Citation Injection]
    Reflector -- Ambiguous Context --> Reformulate[Query Reformulator] --> ReQuery[Re-Query Hybrid Store] --> Generator
    
    Generator --> AuditLog[Neon chat_audit_logs\nCompliance Audit Trail & Latency Tracking]
    Generator --> Delivery[Next.js 16 Edge Client / Streamlit Dashboard / FastAPI REST]
```

---

## Engineering Decisions & Architectural Justifications

Building an intelligence engine for statutory compliance requires significantly higher precision, lower hallucination risk, and stricter fault tolerance than generic consumer chatbots. Every architectural choice in ComplyGH was made to address concrete legal, operational, and computational challenges.

---

### 1. Dual-Tier Storage Layer: Cloud Neon PostgreSQL with Local ChromaDB Fallback

* **The Problem:** Cloud-native vector databases introduce external network latency, cloud connection dropouts, and cold-start connection limits. Conversely, purely local vector stores (like SQLite-based ChromaDB) cannot handle cloud concurrency, lack enterprise relational joins, and make sharing state across serverless instances difficult.
* **The Decision:** Implemented a **dual-tier failover storage engine**:
  1. **Primary (Cloud):** Neon Serverless PostgreSQL with `pgvector` for cloud production.
  2. **Secondary (Local):** Local ChromaDB persistent storage with an in-memory BM25 index for offline development and instant fallback.
* **Why It Matters:**
  * **Relational Joins with Vector Search:** Neon allows executing dense vector similarity alongside relational metadata filters (`d.status = 'ACTIVE'`, `a.institution_type = 'COMMERCIAL_BANK'`) in a single atomic SQL statement.
  * **Zero Downtime Fallback:** If cloud network connectivity drops, the system seamlessly degrades to local ChromaDB without throwing 500 errors or failing client requests.

---

### 2. Hybrid Retrieval: Dense Embeddings + Lexical Full-Text Search (BM25 & GIN `tsvector`)

* **The Problem:** Dense vector embeddings (semantic search) capture conceptual similarity but consistently fail on exact legal nomenclature, specific penal codes, statutory section numbers (e.g., *"Section 29(2) of Act 930"*), and domain-specific acronyms (*"CAR"*, *"SDI"*, *"EMI"*, *"AML/CFT"*).
* **The Decision:** Combined dense semantic search with lexical keyword matching:
  * **In Neon PostgreSQL:** Single-statement scoring combining **70% dense cosine distance** (`c.embedding <=> %s`) and **30% full-text keyword rank** (`ts_rank(tsv_tokens, plainto_tsquery('english', %s))`).
  * **In ChromaDB Fallback:** Inverted-index BM25 combined with dense vectors via **Reciprocal Rank Fusion (RRF)** ($k=60$).
* **Why It Matters:** Hybrid retrieval guarantees that statutory clauses with exact numbers and acronyms rank at the very top of context windows, eliminating retrieval misses on specific legal queries.

---

### 3. Sliding-Window Token-Bounded Chunking with Overlap (500 Tokens / 75 Overlap)

* **The Problem:** Regulatory documents consist of heavily nested clauses, statutory provisos, and cross-references. Character-based chunking chops sentences mid-word, while arbitrary paragraph splitting separates legal conditions from their exceptions and penalties. Overly large chunks dilute vector similarity, while microscopic chunks lose legislative context.
* **The Decision:** Implemented a **token-bounded sliding window** ([src/chunk.py](file:///c:/Users/DELL/OneDrive/Desktop/Rag_Project/src/chunk.py)) targeting **500 tokens** per chunk with a **75-token sliding overlap** (15% boundary context).
* **Why It Matters:**
  * **Contextual Cohesion:** The 75-token overlap prevents legislative definitions and qualifying clauses from being severed across chunk boundaries.
  * **Optimal Embedding Density:** 500 tokens matches the optimal semantic representation window for `all-MiniLM-L6-v2` (512 max input length), maximizing cosine similarity precision.

---

### 4. Traceable Citation & Page-Level Provenance Architecture

* **The Problem:** In corporate governance and legal audits, an AI response without exact statutory attribution is legally inadmissible and presents severe regulatory risk. Generic RAG systems cite only document names, forcing compliance officers to hunt through 200-page Acts to verify claims.
* **The Decision:** Mandated structured metadata extraction during PDF ingestion: every single chunk permanently binds `source_filename`, `page_number`, and `section_title` into Neon and ChromaDB. The synthesis prompt explicitly enforces markdown citations linking every statement to its exact source and page.
* **Why It Matters:**
  * Turns black-box AI responses into verifiable legal evidence.
  * Allows compliance teams to inspect the underlying PDF directly through the API's `/documents/pdf/{filename}` streaming endpoint.

---

### 5. 3-Stage Agentic Reasoning: Rewriting, Routing, and Corrective Self-Reflection (CRAG)

* **The Problem:** Naive RAG architectures blindly embed raw user queries and search the entire vector space. This causes three severe failure modes:
  1. **Anaphoric Ambiguity:** Conversational queries with pronouns (*"What are its capital requirements?"*) fail retrieval because the entity is missing.
  2. **Cross-Statute Pollution:** Vector similarity may pull commercial banking rules for a mobile money question.
  3. **Low-Quality Context Hallucination:** When retrieved chunks are marginally relevant, naive generators hallucinate plausible-sounding legal text.
* **The Decision:** Built a 3-stage agentic reasoning pipeline ([src/rag_pipeline.py](file:///c:/Users/DELL/OneDrive/Desktop/Rag_Project/src/rag_pipeline.py)):
  1. **Conversational Query Rewriting:** Uses conversation turns to expand ambiguous follow-ups into standalone, entity-rich legal queries.
  2. **Dynamic Regulatory Routing:** Classifies query intent against the regulatory document catalog to constrain vector searches exclusively to applicable Acts/Directives.
  3. **Corrective RAG (CRAG) Self-Reflection:** An LLM evaluates retrieved context sufficiency. If information is incomplete or ambiguous, it reformulates the query into high-intent legal keywords and re-queries the database before generation.
* **Why It Matters:** Eliminates cross-statute pollution, resolves conversational context across multi-turn chats, and prevents the generator from operating on weak context.

---

### 6. Strict Grounding Guardrails & Deterministic Refusal (Precision > Recall)

* **The Problem:** In regulatory compliance, a false positive (hallucinating an incorrect capital reserve requirement or non-existent penalty) is catastrophically worse than stating that information is unavailable.
* **The Decision:** System prompts enforce strict negative constraints:
  > *"Answer ONLY based on the provided excerpts. If the answer cannot be determined from the context, state: 'This information is not found in the indexed Bank of Ghana regulatory documents.' Do NOT use external knowledge."*
* **Why It Matters:**
  * Prioritizes high precision over unconstrained recall.
  * Protects financial institutions from regulatory non-compliance caused by AI hallucination.

---

### 7. Custom Thread-Safe Serverless Connection Pooling (`NeonConnectionPool`)

* **The Problem:** Serverless PostgreSQL providers like Neon terminate idle connections during scale-to-zero periods. Under concurrent async API requests in FastAPI, sharing a single `psycopg` connection causes cursor collisions, broken pipe errors (`psycopg.OperationalError`), and thread deadlocks. Conversely, heavyweight connection pool libraries introduce complex C-extensions that break on minimal container runtimes.
* **The Decision:** Engineered an in-memory, thread-safe connection pool using Python’s standard library `queue.Queue` and `threading.Lock`:
  * Implements an active liveness ping (`SELECT 1;`) to detect and discard terminated serverless connections before checkout.
  * Employs Python context managers (`with self.pg_connection() as conn:`) for guaranteed check-in and leak prevention.
* **Why It Matters:** Provides high-throughput concurrent query handling without broken pipes or thread contention during Neon scale-to-zero wakeups.

---

### 8. Memory-Constrained Container Architecture (Render 512MB RAM Optimization)

* **The Problem:** Deploying Python machine learning applications to free or cost-effective cloud tiers (such as Render Free Tier or Hugging Face Spaces) imposes a strict **512MB RAM ceiling**. Default PyTorch packages bundle ~2.5GB of CUDA libraries and initialize multi-threaded BLAS memory pools across all detected host cores (often 32–64 virtual cores), consuming 550MB+ on startup and triggering the Linux Out-Of-Memory (OOM) killer.
* **The Decision:**
  * **Lightweight CPU-Only PyTorch:** Installed PyTorch explicitly from the CPU wheel index (`--index-url https://download.pytorch.org/whl/cpu`), slashing image size and memory usage by **>70%**.
  * **Host Thread Clamping:** Enforced single-thread execution in Dockerfile and code:
    ```bash
    ENV TORCH_NUM_THREADS=1
    ENV OMP_NUM_THREADS=1
    ENV OPENBLAS_NUM_THREADS=1
    ENV MKL_NUM_THREADS=1
    ```
    coupled with runtime programmatic clamping: `torch.set_num_threads(1)`.
  * **Single Worker Execution:** Configured Uvicorn with `--workers 1`.
* **Why It Matters:** Container memory consumption remains stable at **~150MB–200MB**, guaranteeing zero OOM kills while leaving ample headroom for concurrent requests.

---

### 9. Pre-Baked Embedding Weights in Docker Image

* **The Problem:** When `SentenceTransformer("all-MiniLM-L6-v2")` initializes at runtime in an empty container, it downloads model weights (~100MB) from the Hugging Face Hub. On shared cloud IPs, unauthenticated Hugging Face requests are heavily rate-limited, adding 30–60 seconds of cold-start latency and triggering client timeouts.
* **The Decision:** Pre-downloaded the model weights into the container image during the Docker build stage:
  ```dockerfile
  ENV HF_HOME=/home/user/.cache
  RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
  ```
* **Why It Matters:** Eliminates all external runtime network dependencies for embeddings. SentenceTransformer loads from local disk in **<0.5 seconds**.

---

### 10. Non-Blocking Server Lifespan & Instant Port Binding

* **The Problem:** Cloud orchestrators (Render, AWS App Runner, Hugging Face) monitor port binding with short startup timeouts. Running synchronous database warming or model downloads inside FastAPI's `lifespan` blocks the event loop, causing cloud orchestrators to kill the container with *"No open ports detected"*.
* **The Decision:** Decoupled port binding from background database warming. The server binds to `0.0.0.0:$PORT` within **100 milliseconds**, while database connection verification runs in a decoupled background task (`asyncio.create_task`).
* **Why It Matters:** Guarantees instant pass on cloud health check probes and eliminates port scanning timeouts.

---

### 11. Architectural Decoupling: Edge Frontend + Headless Python API

* **The Problem:** Monolithic full-stack Python frameworks (such as Streamlit alone) struggle with advanced DOM control, mobile responsiveness, and client-side caching.
* **The Decision:** Decoupled the architecture into a headless Python FastAPI backend (optimized for data processing and vector math) and a modern **Next.js 16 (App Router) + React 19 + Tailwind CSS v4** frontend deployed on Vercel's global edge network.
* **Why It Matters:**
  * Static UI assets and chat state (`localStorage`) are served instantly from global edge CDNs.
  * Backend resources are dedicated solely to retrieval and LLM synthesis.
  * Wildcard CORS regex (`.*\.vercel\.app`) enables zero-configuration Vercel preview and production deployments.

---

### 12. Automated Tri-Metric Evaluation Engine (LLM-as-a-Judge)

* **The Problem:** Traditional NLP metrics (BLEU, ROUGE) measure n-gram overlap rather than semantic correctness, making them useless for measuring RAG quality where statutory facts must be precisely validated.
* **The Decision:** Implemented a tri-metric evaluation suite ([src/evaluate.py](file:///c:/Users/DELL/OneDrive/Desktop/Rag_Project/src/evaluate.py)) executing:
  1. **Faithfulness:** Verifies every claim in the answer is directly supported by retrieved context (hallucination detection).
  2. **Answer Relevance:** Evaluates how directly the synthesized answer addresses the user's specific prompt.
  3. **Out-of-Domain Refusal:** Tests adversarial non-banking queries (e.g., medical advice, sports) to verify guardrails correctly refuse ungrounded questions.
* **Why It Matters:** Provides quantitative, reproducible quality metrics before releasing pipeline updates or swapping underlying models.

---

## Regulatory Corpus Covered

The system indexes and reasons over official regulatory documents, including:
* **Banks and Specialised Deposit-Taking Institutions Act, 2016 (Act 930)**
* **Payment Systems and Services Act, 2019 (Act 987)**
* **Bank of Ghana Cyber and Information Security Directive (CISD)**
* **Anti-Money Laundering Act, 2020 (Act 1044)**
* **Credit Reporting Act, 2007 (Act 726) & Credit Product Disclosures**
* **Foreign Exchange Directives & Guidelines for Inward Remittance**
* **Digital Credit Services Providers Directives & ICAAP Guidelines**
* **State of the Industry Mobile Money Interoperability Reports**

---

## Project Structure

```
Rag_Project/
├── api.py                      # FastAPI REST application (rate-limited, async, PDF serving)
├── app.py                      # Interactive Streamlit application
├── auto_push.py                # Automated Git synchronization tool
├── Dockerfile                  # Production CPU-optimized, non-root Docker configuration
├── .dockerignore               # Build optimization filter (excludes venv, frontend, git)
├── migrate_chroma_to_neon.py   # Migration tool from ChromaDB to Neon Postgres
├── requirements.txt            # Python dependencies
├── src/                        # Core RAG pipeline modules
│   ├── config.py               # Centralized configuration & environment loader
│   ├── ingest.py               # PDF parser extracting text, page numbers & sections
│   ├── chunk.py                # Sliding-window token-bounded chunker with overlap
│   ├── embed.py                # Vector encoding & ChromaDB upsert pipeline
│   ├── rag_pipeline.py         # Unified agentic pipeline, pool & hybrid search
│   └── evaluate.py             # LLM-as-a-judge benchmarking suite
├── frontend/                   # Modern Next.js 16 Web Application
│   ├── src/app/                # App router (page.tsx, layout.tsx, globals.css)
│   ├── src/components/         # ChatArea.tsx, Sidebar.tsx
│   └── package.json            # Node.js dependencies
└── tests/                      # Automated unit test suite
    ├── test_config.py          # Configuration & prompt validation
    ├── test_chunking.py        # Token sliding-window chunk tests
    ├── test_bm25.py            # Inverted-index BM25 tests
    └── test_api_schemas.py     # FastAPI Pydantic schema validation tests
```

---

## Quickstart & Setup

### 1. Prerequisites
* Python 3.11+
* Node.js 18+ (for Next.js frontend)
* Google Gemini API Key
* (Optional) Neon Serverless PostgreSQL with `pgvector` enabled

### 2. Environment Configuration
Create a `.env` file in the project root:

```bash
# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Neon Serverless Postgres (Optional, degrades to local ChromaDB if omitted)
DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz.neon.tech/neondb?sslmode=require

# Model Configuration
GENERATION_MODEL=gemini-3.8-flash
FAST_MODEL=gemini-3.8-flash

# Allowed CORS Origins
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 3. Backend Setup
```bash
pip install -r requirements.txt
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```
* **Swagger Documentation:** `http://localhost:8000/docs`
* **Healthcheck:** `http://localhost:8000/health`

### 4. Frontend Setup (Next.js)
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## Testing & Benchmarking

### Run Automated Unit Tests
```bash
python -m unittest discover tests
```
*Executes 13 unit tests across configuration, token-bounded chunking, inverted-index BM25 ranking, and API schema validation.*

### Run Evaluation Suite (LLM-as-a-Judge)
```bash
python -m src.evaluate
```
*Evaluates Faithfulness, Relevance, and Out-of-Domain Refusal across in-domain banking queries and adversarial trick questions.*

---

## API Reference

### `POST /ask`
Submits a compliance query with conversation history, corrective reflection, and document routing flags.

**Request Body:**
```json
{
  "question": "What is the minimum capital adequacy ratio for a bank?",
  "history": [],
  "corrective": true,
  "routing": true,
  "use_hybrid": true,
  "top_k": 5,
  "institution_type": "COMMERCIAL_BANK"
}
```

**Response (200 OK):**
```json
{
  "answer": "Under Section 29(2) of the Banks and Specialised Deposit-Taking Institutions Act, 2016 (Act 930), a bank must maintain a minimum capital adequacy ratio of at least ten percent...",
  "sources": [
    {
      "source_filename": "BANKS-AND-SPECIALISED-DEPOSIT-ACT-2016.pdf",
      "page_number": "28",
      "section_title": "Section 29",
      "text": "..."
    }
  ],
  "rewritten_query": null,
  "routed_to": ["BANKS-AND-SPECIALISED-DEPOSIT-ACT-2016.pdf"],
  "reformulated_query": null,
  "latency_sec": 1.15
}
```

### `GET /documents`
Returns all active regulatory documents currently indexed in Neon PostgreSQL or local storage.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
