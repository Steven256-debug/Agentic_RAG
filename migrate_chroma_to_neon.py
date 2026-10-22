"""
Migration script: Local ChromaDB -> Neon Serverless Postgres with pgvector

Transfers all regulatory documents, 4,659 text chunks, and their 384-dimensional
MiniLM embeddings into production-ready relational tables on Neon.
"""

import os
import sys
import time
import uuid
from pathlib import Path
from dotenv import load_dotenv
import numpy as np

import chromadb
import psycopg
from pgvector.psycopg import register_vector

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
VECTORDB_DIR = PROJECT_ROOT / "data" / "vectordb"
CHROMA_COLLECTION_NAME = "rag_documents"


def determine_category_and_applicability(filename: str):
    """Assigns regulatory categories and target financial institution tiers."""
    fn = filename.upper()
    category = "Banking & SDIs"
    tiers = ["COMMERCIAL_BANK", "SDI"]

    if "CYBER" in fn or "SECURITY" in fn:
        category = "Cybersecurity & Technology"
        tiers = ["COMMERCIAL_BANK", "SDI", "EMI_MOBILE_MONEY", "PSP"]
    elif "PAYMENT" in fn or "ELECTRONIC" in fn or "MONEY" in fn:
        category = "Payment Systems & FinTech"
        tiers = ["EMI_MOBILE_MONEY", "PSP", "COMMERCIAL_BANK"]
    elif "CREDIT" in fn:
        category = "Credit Reporting"
        tiers = ["COMMERCIAL_BANK", "SDI", "CREDIT_BUREAU"]
    elif "ANTI-MONEY" in fn or "AML" in fn:
        category = "AML / CFT Compliance"
        tiers = ["COMMERCIAL_BANK", "SDI", "EMI_MOBILE_MONEY", "FOREX_BUREAU", "PSP"]
    elif "FOREIGN" in fn or "FOREX" in fn:
        category = "Foreign Exchange"
        tiers = ["COMMERCIAL_BANK", "FOREX_BUREAU"]

    return category, tiers


def run_migration():
    if not DATABASE_URL:
        print("=" * 70)
        print("ERROR: DATABASE_URL is not set in your .env file.")
        print()
        print("To connect your Neon Postgres database:")
        print("1. Open your Neon project branch:")
        print("   https://console.neon.tech/app/projects/fancy-recipe-84136740/branches/br-shy-snow-b80zxm6h")
        print("2. In the 'Connection Details' widget, copy your connection string.")
        print("3. Add it to .env like this:")
        print("   DATABASE_URL=postgresql://neondb_owner:YOUR_PASSWORD@ep-xyz.neon.tech/neondb?sslmode=require")
        print("=" * 70)
        sys.exit(1)

    print("=" * 70)
    print("ComplyGH: ChromaDB -> Neon Postgres Migration")
    print("=" * 70)

    # 1. Connect to Neon
    print("\n[1/5] Connecting to Neon Postgres...")
    t0 = time.time()
    try:
        conn = psycopg.connect(DATABASE_URL, autocommit=True)
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
        register_vector(conn)
        print(f"Connected to Neon & enabled pgvector in {time.time() - t0:.2f}s")
    except Exception as e:
        print(f"Failed to connect to Neon Postgres: {e}")
        sys.exit(1)

    cur = conn.cursor()

    # 2. Setup Schema & Extensions
    print("\n[2/5] Creating relational schema...")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        title VARCHAR(255) NOT NULL,
        filename VARCHAR(255) UNIQUE NOT NULL,
        category VARCHAR(100),
        status VARCHAR(50) DEFAULT 'ACTIVE',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS document_applicability (
        id SERIAL PRIMARY KEY,
        document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
        institution_type VARCHAR(100) NOT NULL,
        CONSTRAINT unique_doc_tier UNIQUE (document_id, institution_type)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS document_chunks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
        source_filename VARCHAR(255) NOT NULL,
        page_number INT NOT NULL,
        section_title VARCHAR(255),
        chunk_text TEXT NOT NULL,
        embedding vector(384),
        tsv_tokens tsvector GENERATED ALWAYS AS (to_tsvector('english', chunk_text)) STORED
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_audit_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        session_id VARCHAR(100),
        user_query TEXT NOT NULL,
        assistant_answer TEXT NOT NULL,
        routed_to TEXT[],
        latency_sec FLOAT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """)
    print("Schema initialized successfully.")

    # 3. Read ChromaDB records
    print("\n[3/5] Extracting chunks and vectors from local ChromaDB...")
    t0 = time.time()
    chroma_client = chromadb.PersistentClient(path=str(VECTORDB_DIR))
    collection = chroma_client.get_collection(CHROMA_COLLECTION_NAME)
    records = collection.get(include=["documents", "metadatas", "embeddings"])

    ids = records.get("ids", [])
    docs = records.get("documents", [])
    metas = records.get("metadatas", [])
    embeddings = records.get("embeddings", [])

    total_chunks = len(ids)
    print(f"Loaded {total_chunks} chunks from ChromaDB in {time.time() - t0:.2f}s.")

    # 4. Populate Documents Catalog
    print("\n[4/5] Populating documents catalog and applicability tiers...")
    unique_filenames = sorted(list({m.get("source_filename", "Unknown.pdf") for m in metas if m}))
    doc_id_map = {}

    for fname in unique_filenames:
        title = fname.replace("-", " ").replace(".pdf", "").title()
        category, tiers = determine_category_and_applicability(fname)

        cur.execute(
            """
            INSERT INTO documents (title, filename, category, status)
            VALUES (%s, %s, %s, 'ACTIVE')
            ON CONFLICT (filename) DO UPDATE 
            SET title = EXCLUDED.title, category = EXCLUDED.category
            RETURNING id;
            """,
            (title, fname, category)
        )
        doc_uuid = cur.fetchone()[0]
        doc_id_map[fname] = doc_uuid

        for tier in tiers:
            cur.execute(
                """
                INSERT INTO document_applicability (document_id, institution_type)
                VALUES (%s, %s)
                ON CONFLICT (document_id, institution_type) DO NOTHING;
                """,
                (doc_uuid, tier)
            )

    print(f"Cataloged {len(doc_id_map)} official Bank of Ghana regulatory documents.")

    # 5. Insert Chunks with Vectors
    print("\n[5/5] Bulk inserting chunks and vector embeddings into Neon...")
    t0 = time.time()
    
    # Clear existing chunks if re-running
    cur.execute("TRUNCATE TABLE document_chunks CASCADE;")

    batch_size = 250
    insert_sql = """
    INSERT INTO document_chunks (
        document_id, source_filename, page_number, section_title, chunk_text, embedding
    ) VALUES (%s, %s, %s, %s, %s, %s);
    """

    for i in range(0, total_chunks, batch_size):
        batch_vals = []
        for j in range(i, min(i + batch_size, total_chunks)):
            meta = metas[j] or {}
            fname = meta.get("source_filename", "Unknown.pdf")
            doc_id = doc_id_map.get(fname)
            page_raw = meta.get("page_number", 1)
            try:
                page_num = int(page_raw)
            except (ValueError, TypeError):
                page_num = 1
            section = meta.get("section_title") or "Unknown"
            text = docs[j]
            emb = np.array(embeddings[j], dtype=np.float32) if embeddings is not None and len(embeddings) > j else None

            batch_vals.append((doc_id, fname, page_num, section, text, emb))

        cur.executemany(insert_sql, batch_vals)
        sys.stdout.write(f"\rMigrated {min(i + batch_size, total_chunks)} / {total_chunks} chunks...")
        sys.stdout.flush()

    print(f"\nAll {total_chunks} chunks migrated in {time.time() - t0:.2f}s.")

    # 6. Create Indexes
    print("\nBuilding HNSW vector and GIN full-text indexes on Neon...")
    t0 = time.time()
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_chunks_embedding 
    ON document_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
    """)
    cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_chunks_tsv 
    ON document_chunks USING gin (tsv_tokens);
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON document_chunks (document_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_applicability_tier ON document_applicability (institution_type);")
    print(f"Indexes built in {time.time() - t0:.2f}s.")

    # Verify
    cur.execute("SELECT COUNT(*) FROM document_chunks;")
    count = cur.fetchone()[0]
    print("\n" + "=" * 70)
    print(f"SUCCESS: Neon Postgres database is fully populated with {count} chunks!")
    print("=" * 70)

    cur.close()
    conn.close()


if __name__ == "__main__":
    run_migration()
