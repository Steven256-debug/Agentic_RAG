"""
Chunking Module for Ingested Documents.
Applies token-bounded sliding window with overlap, keeping legal clauses organized by page.
Includes resilient fallback tokenization that functions offline.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any

from .config import (
    PROCESSED_DATA_DIR,
    CHUNKS_DATA_DIR,
    CHUNK_MAX_TOKENS,
    CHUNK_OVERLAP,
)

_cached_encoder = None

def get_resilient_encoder():
    """
    Returns tiktoken encoder if available and cached, or a fast offline
    word-based tokenizer if tiktoken cannot access remote assets.
    """
    global _cached_encoder
    if _cached_encoder is not None:
        return _cached_encoder

    try:
        import tiktoken
        encoder = tiktoken.get_encoding("cl100k_base")
        # Test encode to ensure weights are accessible
        _ = encoder.encode("test")
        _cached_encoder = encoder
        return _cached_encoder
    except Exception:
        class LocalWordTokenizer:
            """Fast, offline tokenizer approximating subword tokens (~0.75 words per token)."""
            def encode(self, text: str) -> List[str]:
                return text.split()

            def decode(self, tokens: List[str]) -> str:
                return " ".join(tokens)

        _cached_encoder = LocalWordTokenizer()
        return _cached_encoder


def get_chunks(text: str, max_tokens: int = CHUNK_MAX_TOKENS, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Splits text into chunks of roughly `max_tokens` with `overlap`.
    
    Why overlap matters:
    Using an overlap prevents slicing a clause or sentence mid-stream, preserving statutory
    context at chunk boundaries so the LLM retains semantic coherence.
    """
    if not text or not text.strip():
        return []

    encoder = get_resilient_encoder()
    tokens = encoder.encode(text)

    chunks = []
    i = 0
    step = max(1, max_tokens - overlap)

    while i < len(tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk_text = encoder.decode(chunk_tokens)
        if chunk_text.strip():
            chunks.append(chunk_text.strip())
        i += step

    return chunks


def process_chunking(
    processed_dir: Path = PROCESSED_DATA_DIR,
    chunks_dir: Path = CHUNKS_DATA_DIR,
    max_tokens: int = CHUNK_MAX_TOKENS,
    overlap: int = CHUNK_OVERLAP
) -> Path:
    processed_path = Path(processed_dir)
    chunks_path = Path(chunks_dir)
    chunks_path.mkdir(parents=True, exist_ok=True)

    all_chunks: List[Dict[str, Any]] = []
    total_tokens = 0
    encoder = get_resilient_encoder()

    json_files = list(processed_path.glob("*.json"))
    if not json_files:
        print(f"No processed JSON files found in {processed_path}. Run ingestion first.")
        return chunks_path / "chunks.json"

    print(f"Processing chunking across {len(json_files)} documents...")

    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8") as f:
            document_data = json.load(f)

        for block_idx, page_data in enumerate(document_data):
            source_filename = page_data.get("source_filename", json_file.stem + ".pdf")
            page_number = page_data.get("page_number", 1)
            section_title = page_data.get("section_title")
            text = page_data.get("text", "")

            # Chunk per page to keep statutory clauses localized
            page_chunks = get_chunks(text, max_tokens=max_tokens, overlap=overlap)

            for chunk_index, chunk_text in enumerate(page_chunks):
                file_stem = os.path.splitext(source_filename)[0]
                chunk_id = f"{file_stem}_p{page_number}_b{block_idx}_c{chunk_index}"

                chunk_obj = {
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "source_filename": source_filename,
                    "page_number": page_number,
                    "section_title": section_title
                }

                all_chunks.append(chunk_obj)
                total_tokens += len(encoder.encode(chunk_text))

    output_file = chunks_path / "chunks.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=4, ensure_ascii=False)

    chunk_count = len(all_chunks)
    avg_size = total_tokens / chunk_count if chunk_count > 0 else 0

    print(f"Chunking complete. Saved {chunk_count} chunks to {output_file}")
    print(f"Average chunk size: {avg_size:.1f} tokens")
    return output_file


if __name__ == "__main__":
    process_chunking()
