import os
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb

def process_embeddings(chunks_file, db_dir):
    chunks_path = Path(chunks_file)
    db_path = Path(db_dir)
    
    if not chunks_path.exists():
        print(f"Chunks file not found at {chunks_file}")
        return
        
    print("Loading chunks...")
    with open(chunks_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
        
    print("Loading embedding model all-MiniLM-L6-v2 (this is very fast!)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    
    print(f"Initializing ChromaDB at {db_path}...")
    client = chromadb.PersistentClient(path=str(db_path))
    
    collection_name = "rag_documents"
    collection = client.get_or_create_collection(name=collection_name)
    
    batch_size = 100
    ids_batch = []
    texts_batch = []
    metadatas_batch = []
    total_stored = 0
    
    for i, chunk in enumerate(chunks):
        chunk_id = chunk["chunk_id"]
        text = chunk["text"]
        
        metadata = {
            "source_filename": chunk.get("source_filename", ""),
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
            print(f"Embedded and stored {total_stored}/{len(chunks)} chunks via MiniLM...", flush=True)
            
            ids_batch = []
            texts_batch = []
            metadatas_batch = []
            
    print(f"\nFinal Confirmation:")
    print(f"Total vectors stored: {total_stored}")
    print(f"Collection name: {collection_name}")

if __name__ == "__main__":
    CHUNKS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "chunks", "chunks.json")
    VECTORDB_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "vectordb")
    
    os.makedirs(VECTORDB_DIR, exist_ok=True)
    
    process_embeddings(CHUNKS_FILE, VECTORDB_DIR)
