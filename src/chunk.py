import os
import json
from pathlib import Path
import tiktoken

def get_chunks(text, max_tokens=400, overlap=50):
    """
    Splits text into chunks of roughly `max_tokens` with an overlap.
    
    Why overlap matters:
    Using an overlap avoids cutting a clause mid-sentence and losing context 
    at chunk boundaries. In legal and regulatory documents, an incomplete sentence 
    could change the meaning entirely or make it impossible for the LLM to 
    understand the clause.
    """
    if not text:
        return []
        
    encoder = tiktoken.get_encoding("cl100k_base")  # standard encoding for OpenAI models
    tokens = encoder.encode(text)
    
    chunks = []
    i = 0
    while i < len(tokens):
        # Take a slice of up to max_tokens
        chunk_tokens = tokens[i:i + max_tokens]
        chunk_text = encoder.decode(chunk_tokens)
        chunks.append(chunk_text)
        
        # Move forward by max_tokens - overlap, unless we're at the end
        i += max_tokens - overlap
        
    return chunks

def process_chunking(processed_dir, chunks_dir):
    processed_path = Path(processed_dir)
    chunks_path = Path(chunks_dir)
    chunks_path.mkdir(parents=True, exist_ok=True)
    
    all_chunks = []
    total_tokens = 0
    
    encoder = tiktoken.get_encoding("cl100k_base")
    
    # Process each JSON file in the processed directory
    for json_file in processed_path.glob("*.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            document_data = json.load(f)
            
        for block_idx, page_data in enumerate(document_data):
            source_filename = page_data.get("source_filename")
            page_number = page_data.get("page_number")
            section_title = page_data.get("section_title")
            text = page_data.get("text", "")
            
            # We process text per page to avoid chunking across page boundaries,
            # which helps keep legal clauses grouped together.
            page_chunks = get_chunks(text, max_tokens=400, overlap=50)
            
            for chunk_index, chunk_text in enumerate(page_chunks):
                # chunk_id: e.g. filename_page_blockidx_chunkindex
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
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, indent=4, ensure_ascii=False)
        
    chunk_count = len(all_chunks)
    avg_size = total_tokens / chunk_count if chunk_count > 0 else 0
    
    print(f"Chunking complete. Saved to {output_file}")
    print(f"Total chunks: {chunk_count}")
    print(f"Average chunk size: {avg_size:.1f} tokens")

if __name__ == "__main__":
    PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
    CHUNKS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chunks")
    
    process_chunking(PROCESSED_DIR, CHUNKS_DIR)
