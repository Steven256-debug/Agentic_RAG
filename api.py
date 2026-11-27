import asyncio
import logging
import os
import re
import secrets
import sys
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

# Import centralized configuration and pipeline service
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from src.config import ALLOWED_ORIGINS, RAW_DATA_DIR
from src.rag_pipeline import RAGPipeline

logger = logging.getLogger("LexFinAPI")
logging.basicConfig(level=logging.INFO)

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
InstitutionTier = Literal["COMMERCIAL_BANK", "SDI", "EMI_MOBILE_MONEY", "PSP"]


def _verify_optional_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> None:
    """Enforces API key authentication only when API_AUTH_TOKEN is configured."""
    expected = os.getenv("API_AUTH_TOKEN", "").strip()
    if not expected:
        return

    provided = (x_api_key or "").strip()
    if not provided and authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer":
            provided = token.strip()

    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized request.",
        )


def _resolve_safe_pdf_path(filename: str) -> Path:
    """Validates and resolves a PDF filename inside RAW_DATA_DIR."""
    clean_name = Path(filename).name
    if (
        not filename
        or filename != clean_name
        or ".." in filename
        or not clean_name.lower().endswith(".pdf")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document filename.",
        )

    raw_root = RAW_DATA_DIR.resolve()
    candidate = (raw_root / clean_name).resolve()
    if not candidate.is_relative_to(raw_root):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document path.",
        )
    if not candidate.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return candidate


# --- Request & Response Schemas ---
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"] = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., min_length=1, max_length=6000, description="Content of the message")

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message content must not be blank")
        return stripped


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000, description="User's query")
    history: Optional[List[ChatMessage]] = Field(
        default_factory=list,
        max_length=10,
        description="Previous conversation turns",
    )
    corrective: bool = Field(default=False, description="Enable self-reflection & query reformulation")
    routing: bool = Field(default=False, description="Enable query routing to specific documents")
    use_hybrid: bool = Field(default=True, description="Enable dense + BM25 hybrid retrieval")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of context chunks to retrieve")
    institution_type: Optional[InstitutionTier] = Field(
        default=None,
        description="Optional target tier: COMMERCIAL_BANK, SDI, EMI_MOBILE_MONEY, PSP",
    )
    session_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Optional chat session identifier",
    )

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("question must not be blank")
        return stripped

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not SESSION_ID_PATTERN.fullmatch(cleaned):
            raise ValueError("session_id must contain 1-64 alphanumeric, dash, or underscore characters")
        return cleaned


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
    logger.info("Initializing ComplyGH RAG API Server...")
    pipeline = RAGPipeline.get_instance()
    app.state.pipeline = pipeline

    async def _warmup_background():
        try:
            if pipeline.is_neon_enabled:
                logger.info("Connecting & warming up Neon Serverless Postgres...")
                conn = await asyncio.to_thread(pipeline._get_pg_conn)
                if conn:
                    logger.info("Neon PostgreSQL connected and ready.")
                else:
                    logger.warning("Could not establish connection to Neon PostgreSQL.")
            else:
                logger.warning("DATABASE_URL environment variable is not set; using local fallback if present.")

            logger.info("Pre-loading embedding model in background...")
            await asyncio.to_thread(lambda: pipeline.embedder)
            logger.info("Embedding model pre-loaded and ready.")
        except Exception as e:
            logger.warning(f"Background warmup notice: {e}")

    async def _keep_alive():
        await asyncio.sleep(30)
        interval = 10 * 60
        while True:
            render_url = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
            if render_url:
                ping_url = f"{render_url}/ping"
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        r = await client.get(ping_url)
                    logger.info(f"Keep-alive ping -> {r.status_code}")
                except Exception as e:
                    logger.warning(f"Keep-alive ping failed: {e}")
            await asyncio.sleep(interval)

    asyncio.create_task(_warmup_background())
    asyncio.create_task(_keep_alive())
    logger.info("ComplyGH HTTP server ready and listening on port.")
    yield
    logger.info("Shutting down ComplyGH API server.")


app = FastAPI(
    title="ComplyGH - Regulatory Compliance API",
    description="Intelligent RAG Assistant for Ghanaian Banking, Financial Services, and Cybersecurity Directives",
    version="2.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=(
        r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|"
        r"10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?$"
        r"|^https://[a-zA-Z0-9-]+\.vercel\.app$"
    ),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-API-Key", "Authorization"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


if not RAW_DATA_DIR.exists():
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


# --- Endpoints ---
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for container probes."""
    return {
        "status": "ok",
        "service": "ComplyGH RAG",
    }


@app.get("/ping", tags=["System"])
async def ping():
    """Lightweight keep-alive endpoint."""
    return {"pong": True}


@app.get("/pdfs/{filename}", tags=["Documents"])
async def get_pdf_document(filename: str):
    """Serves validated regulatory PDF documents from RAW_DATA_DIR."""
    pdf_path = _resolve_safe_pdf_path(filename)
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{pdf_path.name}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get(
    "/documents",
    response_model=DocumentListResponse,
    tags=["Documents"],
    dependencies=[Depends(_verify_optional_api_key)],
)
async def list_documents():
    """Returns available regulatory PDFs in the document repository."""
    pipeline: RAGPipeline = app.state.pipeline
    docs = await asyncio.to_thread(pipeline.get_available_documents)
    return DocumentListResponse(documents=docs, count=len(docs))


@app.post(
    "/ask",
    response_model=AskResponse,
    tags=["RAG"],
    dependencies=[Depends(_verify_optional_api_key)],
)
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
        history_dicts = (
            [{"role": m.role, "content": m.content} for m in body.history]
            if body.history
            else []
        )

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

        sources_formatted = [
            SourceItem(
                source_filename=s.get("source_filename", "Unknown"),
                page_number=str(s.get("page_number", "Unknown")),
                section_title=s.get("section_title") or "Unknown",
                text=s.get("text", ""),
            )
            for s in result.get("sources", [])
        ]

        return AskResponse(
            answer=result["answer"],
            sources=sources_formatted,
            rewritten_query=result.get("rewritten_query"),
            routed_to=result.get("routed_to"),
            reformulated_query=result.get("reformulated_query"),
            latency_sec=result.get("latency_sec", 0.0),
        )

    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is temporarily busy. Please try again shortly.",
        )
    except Exception as e:
        err_str = str(e)
        logger.error(f"Error processing /ask request: {err_str}", exc_info=True)
        if "429" in err_str or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Upstream AI provider rate limit reached. Please retry in a few seconds.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal processing error occurred. Please try again later.",
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("API_RELOAD", "false").lower() == "true"
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=reload_enabled)
