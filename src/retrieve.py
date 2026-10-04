import os
import sys
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb

def main():
    VECTORDB_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "vectordb")
    db_path = Path(VECTORDB_DIR)
    
    if not db_path.exists():
        print(f"Vector database not found at {db_path}. Please run Step 3 first.")
        sys.exit(1)
        
    print("Loading embedding model (BAAI/bge-large-en-v1.5)...")
    model = SentenceTransformer("BAAI/bge-large-en-v1.5")
    
    print(f"Connecting to ChromaDB at {db_path}...")
    client = chromadb.PersistentClient(path=str(db_path))
    
    collection_name = "rag_documents"
    try:
        collection = client.get_collection(name=collection_name)
    except Exception as e:
        print(f"Could not find collection '{collection_name}'. Error: {e}")
        sys.exit(1)
        
    print(f"Successfully loaded collection '{collection_name}' with {collection.count()} documents.")
    print("\n--- RAG Retrieval Tester ---")
    print("Type your query below. Type 'exit' to quit.\n")
    
    while True:
        try:
            query = input("\nEnter query: ").strip()
            if not query:
                continue
            if query.lower() == 'exit':
                print("Exiting...")
                break
                
            # Embed the query
            query_embedding = model.encode(query).tolist()
            
            # Query the Chroma collection
            # By default, ChromaDB uses L2 (Euclidean) distance for similarity.
            # What the similarity score means:
            # A lower distance score indicates that the vectors are closer together in the vector space,
            # which generally means higher semantic similarity. So, smaller distance = more relevant!
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=5,
                include=["metadatas", "documents", "distances"]
            )
            
            if not results["ids"][0]:
                print("No results found.")
                continue
                
            print("\n" + "="*50)
            print(f"TOP 5 RESULTS FOR: '{query}'")
            print("="*50 + "\n")
            
            # results is a dictionary with lists of lists (since we queried with 1 embedding, we take index 0)
            ids = results["ids"][0]
            distances = results["distances"][0]
            metadatas = results["metadatas"][0]
            documents = results["documents"][0]
            
            for rank in range(len(ids)):
                chunk_id = ids[rank]
                distance = distances[rank]
                metadata = metadatas[rank]
                text = documents[rank]
                
                source_file = metadata.get("source_filename", "Unknown")
                page_num = metadata.get("page_number", "Unknown")
                section_title = metadata.get("section_title", "Unknown")
                
                print(f"Rank: {rank + 1} | Score (L2 Distance): {distance:.4f} (lower is better)")
                print(f"Chunk ID: {chunk_id}")
                print(f"Source: {source_file} (Page {page_num})")
                print(f"Section: {section_title}")
                print("-" * 50)
                print(f"Text:\n{text}")
                print("="*50 + "\n")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()
