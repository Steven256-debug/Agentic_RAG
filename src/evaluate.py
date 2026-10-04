import os
import sys
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb
from generate import build_context_prompt, call_llm

def main():
    VECTORDB_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "vectordb")
    db_path = Path(VECTORDB_DIR)
    
    if not db_path.exists():
        print(f"Vector database not found at {db_path}. Please run Step 3 first.")
        sys.exit(1)
        
    print("Loading embedding model (BAAI/bge-large-en-v1.5)...")
    model = SentenceTransformer("BAAI/bge-large-en-v1.5")
    
    print(f"Connecting to ChromaDB at {db_path}...")
    client_chroma = chromadb.PersistentClient(path=str(db_path))
    
    collection_name = "rag_documents"
    try:
        collection = client_chroma.get_collection(name=collection_name)
    except Exception as e:
        print(f"Could not find collection '{collection_name}'. Error: {e}")
        sys.exit(1)

    questions = [
        # Mobile money rules
        "What are the requirements for opening a mobile money account?",
        "How are mobile money agents regulated and monitored?",
        
        # Banking capital/liquidity rules
        "What is the minimum capital adequacy ratio for a bank?",
        "What are the liquidity requirements for a specialized deposit-taking institution?",
        
        # GSMA content
        "What guidelines does the GSMA provide regarding mobile money interoperability?",
        
        # Question pulling from multiple source documents
        "Summarize both the capital adequacy requirements for banks and the regulatory requirements for mobile money operators.",
        
        # Another standard question
        "What is the penalty for non-compliance with the minimum capital requirement?",
        
        # Trick questions (not in corpus)
        "What is the capital of Australia?",
        "How do you bake a chocolate cake?",
        "Who won the FIFA World Cup in 2022?"
    ]

    print("\n--- Starting Evaluation ---")
    results_list = []

    for idx, query in enumerate(questions):
        print(f"\nProcessing question {idx+1}/{len(questions)}: {query}")
        
        query_embedding = model.encode(query).tolist()
        
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=5,
            include=["metadatas", "documents", "distances"]
        )
        
        if not results["ids"][0]:
            print("No context found in the database.")
            continue
            
        metadatas = results["metadatas"][0]
        documents = results["documents"][0]
        
        prompt, retrieved_sources = build_context_prompt(query, documents, metadatas)
        
        system_prompt = (
            "Answer ONLY using the provided context. If the context does not contain the answer, "
            "say so explicitly. Always cite which source document and page number your answer comes from."
        )
        
        try:
            answer = call_llm(prompt, system=system_prompt, model="gemini-3.5-flash")
        except Exception as e:
            answer = f"Error generating answer: {str(e)}"
            
        print("Done.")
        
        # Format the result dictionary
        result_entry = {
            "question": query,
            "answer": answer,
            "cited_sources": retrieved_sources,
            "manual_correctness_check": ""  # Blank for manual filling
        }
        results_list.append(result_entry)

    # Save to JSON
    output_file = os.path.join(os.path.dirname(__file__), "..", "data", "eval_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results_list, f, indent=4, ensure_ascii=False)
        
    print(f"\nEvaluation complete. Results saved to {output_file}")

if __name__ == "__main__":
    main()
