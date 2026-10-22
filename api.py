import os
import sys
import asyncio
import logging
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import centralized configuration and pipeline service
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from src.config import RAW_DATA_DIR, ALLOWED_ORIGINS
from src.rag_pipeline import RAGPipeline

logger = logging.getLogger("LexFinAPI")
logging.basicConfig(level=logging.INFO)

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)


# --- Request & Response Schemas ---
class ChatMessage(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Content of the message")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User's query")
    history: Optional[List[ChatMessage]] = Field(default=[], description="Previous conversation turns")
    corrective: bool = Field(default=False, description="Enable self-reflection & query reformulation")
    routing: bool = Field(default=False, description="Enable query routing to specific documents")
    use_hybrid: bool = Field(default=True, description="Enable dense + BM25 hybrid retrieval")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of context chunks to retrieve")


class SourceItem(BaseModel):
    source_filename: str
    page_number: str
    section_title: str
    text: str


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    rewritten_query: Optional[str] = None
    routed_to: Optional[List[str]] = None
    reformulated_query: Optional[str] = None
    latency_sec: float


class DocumentListResponse(BaseModel):
    documents: List[str]
    count: int


# --- Lifespan Context Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing ComplyGH RAG Service on startup...")
    # Pre-warm singleton pipeline instance in background threadpool
    pipeline = await asyncio.to_thread(RAGPipeline.get_instance)
    _ = await asyncio.to_thread(lambda: pipeline.chroma_collection)
    _ = await asyncio.to_thread(lambda: pipeline.embedder)
    # Pre-warm BM25 inverted index & embedding model so the 1st request responds in seconds
    logger.info("Warming up BM25 lexical index...")
    await asyncio.to_thread(pipeline._init_bm25_if_needed)
    logger.info("Warming up embedding encoder...")
    await asyncio.to_thread(lambda: pipeline.embedder.encode("warmup query"))
    app.state.pipeline = pipeline
    logger.info("ComplyGH RAG Service successfully warmed up.")
    yield
    logger.info("Shutting down ComplyGH API server.")


# Initialize FastAPI app
app = FastAPI(
    title="ComplyGH - Regulatory Compliance API",
    description="Intelligent RAG Assistant for Ghanaian Banking, Financial Services, and Cybersecurity Directives",
    version="2.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware configuration supporting localhost and local Wi-Fi / mobile LAN IP
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount raw regulatory PDFs for client-side deep linking (Bug 2 fix: using RAW_DATA_DIR)
if not RAW_DATA_DIR.exists():
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/pdfs", StaticFiles(directory=str(RAW_DATA_DIR)), name="pdfs")


# --- Endpoints ---
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for container probes."""
    return {"status": "ok", "service": "ComplyGH RAG"}



@app.get("/documents", response_model=DocumentListResponse, tags=["Documents"])
async def list_documents():
    """Returns available regulatory PDFs in the document repository."""
    pipeline: RAGPipeline = app.state.pipeline
    docs = await asyncio.to_thread(pipeline.get_available_documents)
    return DocumentListResponse(documents=docs, count=len(docs))


@app.post("/ask", response_model=AskResponse, tags=["RAG"])
@limiter.limit("15/minute")
@limiter.limit("200/day")
async def ask_question(request: Request, body: AskRequest):
    """
    Primary RAG generation endpoint:
    - Conversational query rewriting
    - Optional dynamic document routing
    - Hybrid dense + BM25 retrieval
    - Optional corrective reflection & reformulation
    - Grounded citation generation
    """
    pipeline: RAGPipeline = app.state.pipeline

    try:
        # Convert Pydantic chat messages to dict format
        history_dicts = [{"role": m.role, "content": m.content} for m in body.history] if body.history else []

        # Run pipeline in worker threadpool to keep FastAPI async event loop unblocked (Bug 3 fix)
        result = await asyncio.to_thread(
            pipeline.execute_rag,
            question=body.question,
            history=history_dicts,
            corrective=body.corrective,
            routing=body.routing,
            use_hybrid=body.use_hybrid,
            top_k=body.top_k
        )

        sources_formatted = [
            SourceItem(
                source_filename=s["source_filename"],
                page_number=str(s["page_number"]),
                section_title=s["section_title"],
                text=s["text"]
            )
            for s in result["sources"]
        ]

        return AskResponse(
            answer=result["answer"],
            sources=sources_formatted,
            rewritten_query=result.get("rewritten_query"),
            routed_to=result.get("routed_to"),
            reformulated_query=result.get("reformulated_query"),
            latency_sec=result.get("latency_sec", 0.0)
        )

    except Exception as e:
        err_str = str(e)
        logger.error(f"Error processing /ask request: {err_str}", exc_info=True)
        if "429" in err_str or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Upstream AI provider rate limit reached. Please retry in a few seconds."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal processing error occurred: {err_str}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
