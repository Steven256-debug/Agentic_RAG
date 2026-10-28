import os
from pathlib import Path
from dotenv import load_dotenv

# Base directories
SRC_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SRC_DIR.parent

# Load environment variables from .env
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CHUNKS_DATA_DIR = DATA_DIR / "chunks"
VECTORDB_DIR = DATA_DIR / "vectordb"
EVAL_RESULTS_FILE = DATA_DIR / "eval_results.json"
CHAT_HISTORY_FILE = DATA_DIR / "chat_history.json"

# ChromaDB & Database configuration
CHROMA_COLLECTION_NAME = "rag_documents"
DATABASE_URL = os.getenv("DATABASE_URL")

# Model configuration
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
GENERATION_MODEL_NAME = os.getenv("GENERATION_MODEL", "gemini-3.8-flash")
FAST_MODEL_NAME = os.getenv("FAST_MODEL", "gemini-3.8-flash")

# RAG hyper-parameters
DEFAULT_TOP_K = int(os.getenv("TOP_K", "5"))
CHUNK_MAX_TOKENS = int(os.getenv("CHUNK_MAX_TOKENS", "400"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# Guardrail & System Prompts
SYSTEM_PROMPT = (
    "You are ComplyGH, an expert regulatory intelligence assistant specializing in "
    "Ghanaian financial regulations, banking laws, cybersecurity directives, and mobile money rules.\n\n"
    "CRITICAL RULES:\n"
    "1. Answer ONLY using the provided context from official documents.\n"
    "2. If the context does not contain sufficient information to answer the question, state clearly and politely "
    "that the provided documents do not contain the answer. Do NOT extrapolate or invent facts.\n"
    "3. Always cite the exact source document name and page number for every substantive claim made.\n"
    "4. Format your answer cleanly and professionally using Markdown (with headers, bullet points, and bold text)."
)


# API Server configuration
_default_origins = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",")
    if origin.strip()
]
