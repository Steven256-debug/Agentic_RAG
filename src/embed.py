"""
Vector Embedding Generation & ChromaDB Storage Module.
Encodes chunked documents and upserts vectors with rich statutory metadata.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import chromadb

from .config import (
    CHUNKS_DATA_DIR,
    VECTORDB_DIR,
    CHROMA_COLLECTION_NAME,
    EMBEDDING_MODEL_NAME,
)


def process_embeddings(
    chunks_file: Path = CHUNKS_DATA_DIR / "chunks.json",
    db_dir: Path = VECTORDB_DIR,
    model_name: str = EMBEDDING_MODEL_NAME,
    collection_name: str = CHROMA_COLLECTION_NAME,
    batch_size: int = 100,
    reset: bool = False
):
    chunks_path = Path(chunks_file)
    db_path = Path(db_dir)

    if not chunks_path.exists():
        print(f"Chunks file not found at {chunks_path}. Run chunking first.")
        return

    print("Loading chunks...")
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks: List[Dict[str, Any]] = json.load(f)

    print(f"Loading embedding model '{model_name}'...")
    model = SentenceTransformer(model_name)

    print(f"Connecting to ChromaDB at {db_path}...")
    db_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(db_path))

    if reset:
        try:
            client.delete_collection(name=collection_name)
            print(f"Reset: Cleared previous collection '{collection_name}' for clean re-indexing.")
        except Exception:
            pass

    collection = client.get_or_create_collection(name=collection_name)

    ids_batch = []
    texts_batch = []
    metadatas_batch = []
    total_stored = 0

    print(f"Starting batch embedding ({len(chunks)} total chunks in batches of {batch_size})...")

    for i, chunk in enumerate(chunks):
        chunk_id = chunk["chunk_id"]
        text = chunk["text"]

        metadata = {
            "source_filename": chunk.get("source_filename", "Unknown"),
            "page_number": chunk.get("page_number", 0),
            "section_title": chunk.get("section_title") or "Unknown"
        }

        ids_batch.append(chunk_id)
        texts_batch.append(text)
        metadatas_batch.append(metadata)

        if len(ids_batch) == batch_size or i == len(chunks) - 1:
            embeddings_batch = model.encode(texts_batch).tolist()

            collection.upsert(
                ids=ids_batch,
                embeddings=embeddings_batch,
                documents=texts_batch,
                metadatas=metadatas_batch
            )

            total_stored += len(ids_batch)
            if total_stored % 500 == 0 or total_stored == len(chunks):
                print(f"Embedded and stored {total_stored}/{len(chunks)} chunks...", flush=True)

            ids_batch = []
            texts_batch = []
            metadatas_batch = []

    print("\nFinal Confirmation:")
    print(f"Total vectors stored: {total_stored}")
    print(f"Collection name: {collection_name}")
    print(f"Vector dimensions: {model.get_sentence_embedding_dimension()}")


if __name__ == "__main__":
    should_reset = "--reset" in sys.argv
    process_embeddings(reset=should_reset)
