# ComplyGH: Agentic RAG for Bank of Ghana Regulatory Compliance

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16.4-black.svg)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/Neon-pgvector-00e599.svg)](https://neon.tech/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**ComplyGH** (formerly *LexFin AI*) is an enterprise-grade **Agentic Retrieval-Augmented Generation (RAG)** system designed specifically for Ghanaian financial and banking regulations. It automates compliance research across Bank of Ghana (BOG) directives, Acts of Parliament, cybersecurity guidelines, and payment systems rules with exact, verifiable citations down to the page and section header.

---

## Architecture Overview

```mermaid
graph TD
    UserQuery([User Regulatory Query]) --> Rewriter[Conversational Query Rewriter]
    Rewriter --> Router[Dynamic Document Router]
    
    subgraph Storage & Retrieval Layer
        Router --> DualEngine{Neon Postgres Active?}
        DualEngine -- Yes --> Neon[Neon Serverless Postgres\nDense pgvector + GIN tsvector]
        DualEngine -- Fallback --> LocalChroma[ChromaDB + In-Memory BM25\nReciprocal Rank Fusion RRF]
    end

    Neon --> Reflector[Corrective Self-Reflection]
    LocalChroma --> Reflector
    
    Reflector -- Sufficient Context --> Generator[Grounded Answer Synthesizer\nGemini 2.5 Flash]
    Reflector -- Insufficient Context --> Reformulate[Query Reformulation Loop] --> StorageReQuery[Re-Query Hybrid Store] --> Generator
    
    Generator --> AuditLog[Neon chat_audit_logs]
    Generator --> Delivery[Next.js 16 Web App / Streamlit / FastAPI]
```

### Key Agentic Capabilities
1. **Conversational Query Rewriting:** Converts multi-turn conversational follow-ups into standalone, entity-rich queries.
2. **Dynamic Regulatory Routing:** Classifies user intent against the indexed regulatory corpus to filter out cross-regulatory noise.
3. **Corrective RAG (CRAG):** Employs self-reflection before generation. If retrieved context lacks necessary statutory details, the query is automatically reformulated for specialized legal search.
4. **Dual-Tier Hybrid Retrieval:**
   * **Primary (Cloud):** Neon Serverless PostgreSQL with `pgvector` HNSW index combined with GIN `tsvector` full-text search (70% dense cosine similarity + 30% BM25 keyword rank).
   * **Fallback (Local):** Local ChromaDB persistent store with custom in-memory inverted index BM25 using Reciprocal Rank Fusion ($k=60$).
5. **Thread-Safe Connection Pooling:** Built-in connection pool with automatic reconnection and liveness pings optimized for Neon scale-to-zero serverless environments.
6. **Strict Citation Guardrails:** Rejects hallucination. Every claim is attributed to the exact source PDF, page number, and section title.

---

## Regulatory Corpus Covered

The system indexes and reasons over official regulatory documents, including:
* **Banks and Specialised Deposit-Taking Institutions Act, 2016 (Act 930)**
* **Payment Systems and Services Act, 2019 (Act 987)**
* **Bank of Ghana Cyber and Information Security Directive (CISD)**
* **Anti-Money Laundering Act, 2020 (Act 1044)**
* **Credit Reporting Act & Regulations**
* **Foreign Exchange Directives & Notices**
* **State of the Industry Mobile Money Reports**

---

## Project Structure

```
Rag_Project/
├── api.py                      # FastAPI REST application with rate limiting & PDF serving
├── app.py                      # Interactive Streamlit application
├── auto_push.py                # Automated Git synchronization with AI commit messages
├── migrate_chroma_to_neon.py   # Migration tool from ChromaDB to Neon Postgres
├── requirements.txt            # Python dependencies
├── sync.bat                    # Windows one-click sync script
├── src/                        # Core RAG pipeline modules
│   ├── config.py               # Centralized configuration & environment loader
│   ├── ingest.py               # PDF parser extracting text, page numbers & sections
│   ├── chunk.py                # Sliding-window token-bounded chunker
│   ├── embed.py                # Sentence-Transformers vector encoder & upsert
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

# Neon Serverless Postgres Connection String (Optional, degrades to ChromaDB if omitted)
DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz.neon.tech/neondb?sslmode=require

# Model configuration (Optional overrides)
GENERATION_MODEL=gemini-2.5-flash
FAST_MODEL=gemini-2.5-flash-lite

# Allowed CORS Origins
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 3. Backend Setup
Install Python dependencies:

```bash
pip install -r requirements.txt
```

Run the FastAPI backend server:

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```
* Interactive API Documentation (Swagger UI): `http://localhost:8000/docs`
* Healthcheck: `http://localhost:8000/health`

### 4. Frontend Setup (Next.js)
In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser. The frontend automatically discovers backend hosts on your local network/Wi-Fi for mobile testing.

### 5. Streamlit Explorer (Alternative UI)
For a standalone data exploration interface:

```bash
streamlit run app.py
```

---

## Migration & Pipeline Tools

### Migrate ChromaDB to Neon Postgres
To populate Neon Postgres with existing vector embeddings and relational metadata:

```bash
python migrate_chroma_to_neon.py
```

### Ingestion & Chunking Pipeline
To re-process raw PDFs from `data/raw/`:

```bash
python -m src.ingest
python -m src.chunk
python -m src.embed
```

---

## Testing & Benchmarking

### Run Automated Unit Tests
```bash
python -m unittest discover tests
```

### Run Evaluation Suite (LLM-as-a-Judge)
Evaluates Faithfulness, Relevance, and Out-of-Domain Refusal across regulatory and trick queries:

```bash
python -m src.evaluate
```

---

## API Reference

### `POST /ask`
Submit a regulatory question with optional conversation history and feature flags.

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
Returns all active regulatory documents currently available in the index.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
