import os
import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer

VECTORDB_DIR = os.path.join(os.path.dirname(__file__), "data", "vectordb")
client = chromadb.PersistentClient(path=VECTORDB_DIR)

try:
    collection = client.get_collection("rag_documents")
    print(f"Total chunks in collection: {collection.count()}")
    
    # Let's see the exact filenames stored in metadata
    results = collection.get(include=["metadatas"])
    filenames = set()
    for meta in results["metadatas"]:
        filenames.add(meta.get("source_filename", "UNKNOWN"))
    
    print("Filenames in DB:")
    for f in filenames:
        print(f" - {f}")
        
    # Let's do a test query
    model = SentenceTransformer("all-MiniLM-L6-v2")
    query_embedding = model.encode("Anti-Money Laundering Act").tolist()
    q_results = collection.query(query_embeddings=[query_embedding], n_results=2)
    
    print("\nTest query results:")
    print("IDs:", q_results["ids"])
    print("Distances:", q_results["distances"])
    
except Exception as e:
    print(f"Error: {e}")
