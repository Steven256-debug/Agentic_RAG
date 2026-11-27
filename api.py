import asyncio
import logging
import os
import secrets
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Literal, Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Import centralized configuration and pipeline service.
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from src.config import ALLOWED_ORIGINS, RAW_DATA_DIR
from src.rag_pipeline import RAGPipeline

logger = logging.getLogger("LexFinAPI")
logging.basicConfig(level=logging.INFO)

limiter = Limiter(key_func=get_remote_address)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=20_000)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=12_000)
    history: List[ChatMessage] = Field(default_factory=list, max_length=10)
    corrective: bool = False
    routing: bool = False
    use_hybrid: bool = True
    top_k: int = Field(default=5, ge=1, le=20)
    institution_type: Optional[Literal["COMMERCIAL_BANK", "SDI", "EMI_MOBILE_MONEY", "PSP"]] = None
    session_id: Optional[str] = Field(default=None, max_length=36)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        return value

    @field_validator("session_id")
    @classmethod
    def session_id_must_be_uuid(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            try:
                uuid.UUID(value)
            except (ValueError, AttributeError) as exc:
                raise ValueError("session_id must be a UUID") from exc
        return value


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


def require_api_token(authorization: Optional[str] = Header(default=None)) -> None:
    """Protect expensive/data endpoints with a server-side bearer token.

    In production, configure API_ACCESS_TOKEN and arrange for an authenticated
    same-origin proxy/BFF to attach it. Never expose this secret as NEXT_PUBLIC_*.
    """
    expected = os.getenv("API_ACCESS_TOKEN")
    if not expected:
        logger.error("Protected API endpoint called without API_ACCESS_TOKEN configured")
        raise HTTPException(status_code=503, detail="API authentication is not configured")
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Authentication required")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing ComplyGH RAG API Server...")
    pipeline = RAGPipeline.get_instance()
    app.state.pipeline = pipeline

    async def warmup() -> None:
        try:
            if pipeline.is_neon_enabled:
                await asyncio.to_thread(pipeline._get_pg_conn)
            await asyncio.to_thread(lambda: pipeline.embedder)
            logger.info("ComplyGH background initialization complete.")
        except Exception:
            logger.exception("Background initialization failed")

    warmup_task = asyncio.create_task(warmup())
    keep_alive_task = None
    render_url = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
    if render_url.startswith("https://"):
        async def keep_alive() -> None:
            async with httpx.AsyncClient(timeout=15.0) as client:
                while True:
                    await asyncio.sleep(600)
                    try:
                        response = await client.get(f"{render_url}/ping")
                        logger.info("Keep-alive ping returned status %s", response.status_code)
                    except Exception:
                        logger.warning("Keep-alive ping failed", exc_info=True)
        keep_alive_task = asyncio.create_task(keep_alive())

    try:
        yield
    finally:
        tasks = [warmup_task]
        if keep_alive_task is not None:
            tasks.append(keep_alive_task)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        pool = getattr(pipeline, "_pg_pool", None)
        if pool is not None:
            pool.closeall()
        logger.info("ComplyGH API server shut down")


app = FastAPI(
    title="ComplyGH - Regulatory Compliance API",
    description="RAG assistant for Ghanaian financial services and cybersecurity directives",
    version="2.1.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Exact-origin allow-list only. Configure production frontend origins explicitly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health", tags=["System"])
async def health_check():
    pipeline: RAGPipeline = app.state.pipeline
    return {"status": "ok", "service": "ComplyGH RAG", "neon_configured": pipeline.is_neon_enabled}


@app.get("/ping", tags=["System"])
async def ping():
    return {"pong": True}


@app.get("/documents", response_model=DocumentListResponse, tags=["Documents"], dependencies=[Depends(require_api_token)])
async def list_documents():
    pipeline: RAGPipeline = app.state.pipeline
    docs = await asyncio.to_thread(pipeline.get_available_documents)
    return DocumentListResponse(documents=docs, count=len(docs))


@app.get("/pdfs/{filename}", tags=["Documents"])
async def get_pdf(filename: str):
    """Serve only a single PDF directly within the configured raw-documents folder."""
    if Path(filename).name != filename or not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=404, detail="Document not found")
    root = RAW_DATA_DIR.resolve()
    candidate = (root / filename).resolve()
    if candidate.parent != root or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(candidate, media_type="application/pdf", filename=filename, headers={"X-Content-Type-Options": "nosniff"})


@app.post("/ask", response_model=AskResponse, tags=["RAG"], dependencies=[Depends(require_api_token)])
@limiter.limit("15/minute")
@limiter.limit("200/day")
async def ask_question(request: Request, body: AskRequest):
    pipeline: RAGPipeline = app.state.pipeline
    try:
        history_dicts = [{"role": message.role, "content": message.content} for message in body.history]
        result = await asyncio.to_thread(
            pipeline.execute_rag,
            question=body.question,
            history=history_dicts,
            corrective=body.corrective,
            routing=body.routing,
            use_hybrid=body.use_hybrid,
            top_k=body.top_k,
            institution_type=body.institution_type,
            session_id=body.session_id,
        )
        sources = [
            SourceItem(
                source_filename=item.get("source_filename", "Unknown"),
                page_number=str(item.get("page_number", "Unknown")),
                section_title=item.get("section_title") or "Unknown",
                text=item.get("text", ""),
            )
            for item in result.get("sources", [])
        ]
        return AskResponse(
            answer=result["answer"],
            sources=sources,
            rewritten_query=result.get("rewritten_query"),
            routed_to=result.get("routed_to"),
            reformulated_query=result.get("reformulated_query"),
            latency_sec=result.get("latency_sec", 0.0),
        )
    except Exception as exc:
        error_text = str(exc).lower()
        logger.exception("Error processing /ask request")
        if "429" in error_text or "quota" in error_text or "resource_exhausted" in error_text:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="The upstream AI provider is rate limited. Please retry later.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process the request. Please try again.",
        ) from exc


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)
