import os
import sys
from contextlib import asynccontextmanager
from typing import List, Optional, Dict
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import traceback
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import chromadb

# Load environment variables
load_dotenv()

# Add src to path so we can import from generate
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
try:
    from generate import call_llm, build_context_prompt
except ImportError:
    print("Error importing from src/generate.py")
    sys.exit(1)

# Setup rate limiter
limiter = Limiter(key_func=get_remote_address)

# Define models
class Message(BaseModel):
    role: str
    content: str

class AskRequest(BaseModel):
    question: str
    history: Optional[List[Message]] = []
    corrective: bool = False
    routing: bool = False

class Source(BaseModel):
    source_filename: str
    page_number: str
    section_title: str
    text: str

class AskResponse(BaseModel):
    answer: str
    sources: List[Source]
    rewritten_query: Optional[str] = None
    routed_to: Optional[List[str]] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load embedding model
    print("Loading embedding model...")
    app.state.model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # Load ChromaDB
    VECTORDB_DIR = os.path.join(os.path.dirname(__file__), "data", "vectordb")
    print(f"Connecting to ChromaDB at {VECTORDB_DIR}...")
    app.state.client_chroma = chromadb.PersistentClient(path=str(VECTORDB_DIR))
    
    try:
        app.state.collection = app.state.client_chroma.get_collection(name="rag_documents")
        print("Successfully connected to Chroma collection.")
    except Exception as e:
        print(f"Error loading collection: {e}")
        app.state.collection = None
        
    yield
    # Cleanup if necessary

app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Setup CORS
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/documents")
async def get_documents():
    raw_dir = os.path.join(os.path.dirname(__file__), "data", "raw_pdfs")
    available_pdfs = []
    if os.path.exists(raw_dir):
        available_pdfs = [f for f in os.listdir(raw_dir) if f.endswith('.pdf')]
    
    # Fallback to chroma if not found on disk
    if not available_pdfs and app.state.collection:
        try:
            results = app.state.collection.get(include=["metadatas"])
            metadatas = results.get("metadatas", [])
            unique_sources = set()
            for meta in metadatas:
                if meta and "source_filename" in meta:
                    unique_sources.add(meta["source_filename"])
            available_pdfs = list(unique_sources)
        except Exception:
            pass

    return {"documents": available_pdfs}

@app.post("/ask", response_model=AskResponse)
@limiter.limit("10/minute")
@limiter.limit("100/day")
async def ask(request: Request, body: AskRequest):
    if app.state.collection is None:
        raise HTTPException(status_code=500, detail="Database not initialized.")

    query = body.question
    rewritten_query = None
    routed_to = None

    try:
        # 1. Rewrite Query if history is provided
        if body.history:
            recent_history = body.history[-6:]
            history_str = "\n".join([f"{msg.role}: {msg.content}" for msg in recent_history])
            rewrite_prompt = (
                "Given the following conversation history, rewrite the user's latest question into a "
                "standalone, fully descriptive question that can be understood without the history.\n\n"
                f"History:\n{history_str}\n\n"
                f"Latest Question: {body.question}\n\n"
                "Output ONLY the rewritten question without quotes or preamble."
            )
            query = call_llm(rewrite_prompt, model="gemini-3.5-flash-lite")
            rewritten_query = query

        # 2. Routing
        routing_filter = None
        if body.routing:
            docs_resp = await get_documents()
            available_pdfs = docs_resp["documents"]
            if available_pdfs:
                pdf_list_str = "\n".join([f"- {pdf}" for pdf in available_pdfs])
                routing_prompt = (
                    f"Given this question: '{query}' and this list of available documents:\n"
                    f"{pdf_list_str}\n\n"
                    "Which document(s) is this question most likely about? Reply with EXACT filename(s) "
                    "(comma-separated if multiple) or ALL if unclear. Output ONLY the filename(s) or ALL without quotes or preamble."
                )
                route_text = call_llm(routing_prompt, model="gemini-3.5-flash-lite")
                
                if "ALL" not in route_text.upper():
                    selected = [f for f in available_pdfs if f in route_text]
                    if selected:
                        if len(selected) == 1:
                            routing_filter = {"source_filename": selected[0]}
                        else:
                            routing_filter = {"source_filename": {"$in": selected}}
                        routed_to = selected

        # 3. Retrieval
        query_embedding = app.state.model.encode(query).tolist()
        
        search_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": 5,
            "include": ["metadatas", "documents", "distances"]
        }
        if routing_filter:
            search_kwargs["where"] = routing_filter
            
        results = app.state.collection.query(**search_kwargs)
        
        if not results["ids"] or not results["ids"][0]:
            return AskResponse(
                answer="I could not find any relevant information in the documents to answer your question.",
                sources=[],
                rewritten_query=rewritten_query,
                routed_to=routed_to
            )
            
        metadatas = results["metadatas"][0]
        documents = results["documents"][0]
        
        context_prompt, retrieved_sources = build_context_prompt(query, documents, metadatas)
        
        # 4. Corrective RAG (Self-Reflection)
        if body.corrective:
            check_prompt = f"Given this question: '{query}' and these chunks:\n{context_prompt}\n\nAre they sufficient to answer confidently? Reply YES or NO with one-line reason."
            check_text = call_llm(check_prompt, model="gemini-3.5-flash-lite")
            
            if check_text.upper().startswith("NO"):
                reformulate_prompt = (
                    f"The user asked: '{query}'. The initial retrieval was insufficient. "
                    "Rewrite this query into a single, more descriptive search query that might yield better document matches. "
                    "Output ONLY the new query string without quotes or preamble."
                )
                query = call_llm(reformulate_prompt, model="gemini-3.5-flash-lite")
                rewritten_query = query # update rewritten query
                
                # Re-run retrieval
                query_embedding = app.state.model.encode(query).tolist()
                search_kwargs["query_embeddings"] = [query_embedding]
                results = app.state.collection.query(**search_kwargs)
                
                if results["ids"] and results["ids"][0]:
                    metadatas = results["metadatas"][0]
                    documents = results["documents"][0]
                    context_prompt, retrieved_sources = build_context_prompt(query, documents, metadatas)

        # 5. Generate Answer
        system_prompt = (
            "Answer ONLY using the provided context. If the context does not contain the answer, "
            "say so explicitly. Always cite which source document and page number your answer comes from. "
            "Format cleanly with markdown."
        )
        
        answer = call_llm(context_prompt, system=system_prompt, model="gemini-3.5-flash")
        
        # Format sources
        sources = []
        for i in range(len(documents)):
            m = metadatas[i]
            sources.append(Source(
                source_filename=m.get('source_filename', 'Unknown'),
                page_number=str(m.get('page_number', 'Unknown')),
                section_title=m.get('section_title', 'Unknown'),
                text=documents[i]
            ))

        return AskResponse(
            answer=answer,
            sources=sources,
            rewritten_query=rewritten_query,
            routed_to=routed_to
        )

    except Exception as e:
        err_msg = str(e)
        traceback.print_exc()
        if "429" in err_msg or "Quota" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "rate limit" in err_msg.lower():
            raise HTTPException(status_code=429, detail="API Rate Limit Hit. Please try again later.")
        else:
            raise HTTPException(status_code=500, detail={"error": "An internal error occurred", "message": err_msg})
