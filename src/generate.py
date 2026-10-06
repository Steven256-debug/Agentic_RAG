import os
import sys
import time
import argparse
from pathlib import Path
from sentence_transformers import SentenceTransformer
import chromadb
from google import genai
from google.genai import types

client_llm = None

def call_llm(prompt, system=None, model="gemini-3.5-flash"):
    global client_llm
    if client_llm is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("Error: GEMINI_API_KEY environment variable not set.")
            print("Please set it before running this script.")
            sys.exit(1)
        client_llm = genai.Client(api_key=api_key)
        
    config = types.GenerateContentConfig(
        max_output_tokens=1024,
    )
    if system:
        config.system_instruction = system

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client_llm.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )
            return response.text.strip()
        except Exception as e:
            if ("429" in str(e) or "503" in str(e)) and attempt < max_retries - 1:
                print("API overloaded or Rate limit hit. Waiting 35 seconds before retrying...")
                time.sleep(35)
                continue
            raise e

def build_context_prompt(question, documents, metadatas):
    context_parts = []
    sources = []
    
    for i in range(len(documents)):
        metadata = metadatas[i]
        text = documents[i]
        
        source = metadata.get("source_filename", "Unknown")
        page = metadata.get("page_number", "Unknown")
        section = metadata.get("section_title") or "Unknown"
        
        # Keep track of unique sources for printing later
        source_id = f"{source} (Page {page})"
        if source_id not in sources:
            sources.append(source_id)
            
        part = f"--- CHUNK {i+1} ---\nSource: {source}\nPage: {page}\nSection: {section}\nText:\n{text}\n"
        context_parts.append(part)
        
    context_str = "\n".join(context_parts)
    
    prompt = f"""You have been provided with the following context from official documents.

<context>
{context_str}
</context>

Question: {question}
"""
    return prompt, sources

def main():
    parser = argparse.ArgumentParser(description="RAG Generation Tester")
    parser.add_argument("--corrective", action="store_true", help="Enable corrective retrieval (self-reflection)")
    parser.add_argument("--routing", action="store_true", help="Enable query routing to specific documents")
    args = parser.parse_args()

    # The API key and client initialization is now handled lazily inside call_llm()

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
        
    print("\n--- RAG Generation Tester ---")
    print("Type your query below. Type 'exit' to quit.\n")
    
    while True:
        try:
            original_query = input("\nEnter query: ").strip()
            if not original_query:
                continue
            if original_query.lower() == 'exit':
                print("Exiting...")
                break
                
            query = original_query
            reformulated = False
            start_time = time.time()
                
            routing_filter = None
            if args.routing:
                print("Routing query to specific document(s)...")
                routing_prompt = (
                    f"Given this question: '{query}' and this list of available documents:\n"
                    "- The-State-of-the-Industry-Report-2026_English.pdf (Mobile money industry trends and GSMA guidelines)\n"
                    "- BANKS-AND-SPECIALISED-DEPOSIT-ACT-2016.pdf (Banking regulations, capital adequacy, and liquidity requirements)\n"
                    "- Cyber-Information-Security-Directive-2026.pdf (Cybersecurity rules and information security directives)\n\n"
                    "Which document(s) is this question most likely about? Reply with EXACT filename(s) (comma-separated if multiple) or ALL if unclear. Output ONLY the filename(s) or ALL without quotes or preamble."
                )
                
                route_text = call_llm(routing_prompt, model="gemini-3.5-flash-lite")
                print(f"[Routing output: {route_text}]")
                
                valid_files = [
                    "The-State-of-the-Industry-Report-2026_English.pdf",
                    "BANKS-AND-SPECIALISED-DEPOSIT-ACT-2016.pdf",
                    "Cyber-Information-Security-Directive-2026.pdf"
                ]
                
                if "ALL" not in route_text.upper():
                    selected = [f for f in valid_files if f in route_text]
                    if selected:
                        if len(selected) == 1:
                            routing_filter = {"source_filename": selected[0]}
                        else:
                            routing_filter = {"source_filename": {"$in": selected}}
                            
            print("Retrieving context...")
            query_embedding = model.encode(query).tolist()
            
            if routing_filter:
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=5,
                    include=["metadatas", "documents", "distances"],
                    where=routing_filter
                )
            else:
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
            
            if args.corrective:
                print("Running corrective retrieval check (self-reflection)...")
                check_prompt = f"Given this question: '{query}' and these chunks:\n{prompt}\n\nAre they sufficient to answer confidently? Reply YES or NO with one-line reason."
                
                check_text = call_llm(check_prompt, model="gemini-3.5-flash-lite")
                print(f"[Reflection output: {check_text}]")
                
                if check_text.upper().startswith("NO"):
                    print("Reformulating query for better retrieval...")
                    reformulate_prompt = f"The user asked: '{original_query}'. The initial retrieval was insufficient. Rewrite this query into a single, more descriptive search query that might yield better document matches. Output ONLY the new query string without quotes or preamble."
                    
                    query = call_llm(reformulate_prompt, model="gemini-3.5-flash-lite")
                    reformulated = True
                    print(f"[Reformulated Query: {query}]")
                    
                    # Re-run retrieval
                    print("Retrieving context with reformulated query...")
                    query_embedding = model.encode(query).tolist()
                    
                    if routing_filter:
                        results = collection.query(
                            query_embeddings=[query_embedding],
                            n_results=5,
                            include=["metadatas", "documents", "distances"],
                            where=routing_filter
                        )
                    else:
                        results = collection.query(
                            query_embeddings=[query_embedding],
                            n_results=5,
                            include=["metadatas", "documents", "distances"]
                        )
                    
                    if results["ids"][0]:
                        metadatas = results["metadatas"][0]
                        documents = results["documents"][0]
                        prompt, retrieved_sources = build_context_prompt(query, documents, metadatas)
            
            retrieval_time = time.time() - start_time
            if args.corrective:
                print(f"Retrieval phase completed in {retrieval_time:.2f}s")
                
            print("Generating answer via LLM...")
            
            # Why we instruct the model to refuse answering outside context:
            # This is the core mechanism that prevents hallucination in RAG systems.
            # If the LLM is allowed to use its pre-trained knowledge, it might confidently
            # provide an answer that sounds correct but contradicts the specific private or
            # updated documents in our vector database. By restricting it strictly to the
            # provided context, we ensure the answer is grounded, verifiable, and accurate
            # to our specific data corpus.
            
            system_prompt = (
                "Answer ONLY using the provided context. If the context does not contain the answer, "
                "say so explicitly. Always cite which source document and page number your answer comes from."
            )
            
            answer = call_llm(prompt, system=system_prompt, model="gemini-3.5-flash")
            
            print("\n" + "="*50)
            print("ANSWER:")
            print("="*50)
            if reformulated:
                print(f"[Note: Generated using reformulated query: {query}]\n")
            print(answer)
            print("\n" + "-"*50)
            print("SOURCES RETRIEVED:")
            for s in retrieved_sources:
                print(f"- {s}")
            print("="*50 + "\n")
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    main()
