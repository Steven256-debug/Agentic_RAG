"""
RAG Retrieval Verification & Testing Module.
Allows querying the vector database with dense embeddings and hybrid BM25 search.
"""

import os
import sys
from pathlib import Path
from .config import VECTORDB_DIR, CHROMA_COLLECTION_NAME, EMBEDDING_MODEL_NAME
from .rag_pipeline import RAGPipeline


def main():
    if not VECTORDB_DIR.exists():
        print(f"Error: Vector database not found at {VECTORDB_DIR}. Please run ingestion/embedding first.")
        sys.exit(1)

    print(f"Initializing RAG Pipeline with model: {EMBEDDING_MODEL_NAME}...")
    pipeline = RAGPipeline.get_instance()
    
    try:
        collection = pipeline.chroma_collection
        count = collection.count()
    except Exception as e:
        print(f"Could not load ChromaDB collection '{CHROMA_COLLECTION_NAME}': {e}")
        sys.exit(1)

    print(f"Successfully loaded '{CHROMA_COLLECTION_NAME}' ({count} chunks indexed).")
    print("\n--- LexFin AI: Vector & Hybrid Retrieval Tester ---")
    print("Type your query below. Type 'exit' to quit.\n")

    while True:
        try:
            query = input("Enter query: ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit"):
                print("Exiting...")
                break

            # Execute hybrid retrieval via pipeline
            docs, metadatas, distances = pipeline.retrieve(query, top_k=5, use_hybrid=True)

            if not docs:
                print("No relevant chunks found.")
                continue

            print("\n" + "=" * 60)
            print(f"TOP {len(docs)} RETRIEVED CHUNKS FOR: '{query}'")
            print("=" * 60)

            for rank in range(len(docs)):
                text = docs[rank]
                meta = metadatas[rank]
                score = distances[rank]

                source_file = meta.get("source_filename", "Unknown Document")
                page_num = meta.get("page_number", "Unknown")
                section_title = meta.get("section_title") or "Unknown Section"

                print(f"Rank: {rank + 1} | Score: {score:.4f}")
                print(f"Source:  {source_file} (Page {page_num})")
                print(f"Section: {section_title}")
                print("-" * 60)
                # Print clean snippet (up to 400 chars)
                snippet = text.strip()
                if len(snippet) > 400:
                    snippet = snippet[:400] + "..."
                print(snippet)
                print("=" * 60 + "\n")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\n[Error during retrieval] {e}\n")


if __name__ == "__main__":
    main()
