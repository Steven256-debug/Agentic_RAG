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
        
    print("Loading embedding model (this may take a moment to download on first run)...")
    # Using local bge-large-en-v1.5 model as requested
    model = SentenceTransformer("BAAI/bge-large-en-v1.5")
    
    print(f"Initializing ChromaDB at {db_path}...")
    # Initialize a persistent ChromaDB client
    client = chromadb.PersistentClient(path=str(db_path))
    
    # Create or get collection
    collection_name = "rag_documents"
    collection = client.get_or_create_collection(name=collection_name)
    
    # We will process in batches to be efficient
    batch_size = 100
    
    # Lists to hold batch data
    ids_batch = []
    texts_batch = []
    metadatas_batch = []
    
    total_stored = 0
    
    for i, chunk in enumerate(chunks):
        chunk_id = chunk["chunk_id"]
        text = chunk["text"]
        
        # We store the original chunk text alongside the vector (as the document).
        # Why we do this:
        # The vector only helps us perform the semantic search to find the right chunk.
        # But we need to return the actual, human-readable text content at retrieval time 
        # so the LLM can read the text and generate a grounded answer. If we only stored 
        # the embedding, we wouldn't be able to reconstruct the words the user needs to see!
        
        # Note: ChromaDB metadata values must be strings, ints, or floats, so we handle nulls.
        metadata = {
            "source_filename": chunk.get("source_filename", ""),
            "page_number": chunk.get("page_number", 0),
            "section_title": chunk.get("section_title") or "Unknown"
        }
        
        ids_batch.append(chunk_id)
        texts_batch.append(text)
        metadatas_batch.append(metadata)
        
        # If we hit the batch size or the end of the chunks, embed and store
        if len(ids_batch) == batch_size or i == len(chunks) - 1:
            # Generate embeddings for the batch
            embeddings_batch = model.encode(texts_batch).tolist()
            
            # Upsert into Chroma (upsert makes this idempotent; it inserts or updates by ID)
            collection.upsert(
                ids=ids_batch,
                embeddings=embeddings_batch,
                documents=texts_batch,
                metadatas=metadatas_batch
            )
            
            total_stored += len(ids_batch)
            
            # Print progress every 100 chunks (or at the very end)
            print(f"Embedded and stored {total_stored}/{len(chunks)} chunks...")
            
            # Clear batches
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
