import os
import sys
import json
import fitz  # PyMuPDF
from pathlib import Path
import re

def extract_metadata_and_text(pdf_path):
    """
    Reads a PDF and extracts text along with page numbers and section headers.
    
    Why we extract page/section metadata now:
    During the RAG ingestion phase, preserving this metadata is critical so that 
    later when the LLM generates answers based on chunks of this text, we can 
    provide accurate citations (e.g. "Section 1, Page 4") tracing back to the 
    original source document.
    """
    doc = fitz.open(pdf_path)
    extracted_data = []
    
    # A simple regex for detecting section titles like "Section 1", "Article II", "1.2 Title", etc.
    # This is a basic heuristic and might need tuning based on exact document formats.
    section_pattern = re.compile(r'^(Section|Article|Clause|\d+\.?\d*)\s+.*', re.IGNORECASE)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # PyMuPDF's get_text("blocks") returns a list of blocks where each block is:
        # (x0, y0, x1, y1, "lines in block", block_no, block_type)
        blocks = page.get_text("blocks")
        
        # Sort blocks by y0 (vertical position) then x0 (horizontal position) for reading order
        blocks.sort(key=lambda b: (b[1], b[0]))
        
        current_section = None
        current_text = ""
        
        for b in blocks:
            if b[6] == 0:  # 0 indicates text block
                block_text = b[4].strip()
                if not block_text:
                    continue
                
                lines = block_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    # Check if this line is a section header
                    if len(line) < 150 and section_pattern.match(line):
                        # If we already have accumulated text under a prior header (or None),
                        # save it off as a separate record before updating the header.
                        if current_text.strip():
                            extracted_data.append({
                                "source_filename": os.path.basename(pdf_path),
                                "page_number": page_num + 1,
                                "section_title": current_section,
                                "text": current_text.strip()
                            })
                            current_text = ""
                        
                        # Now update the current section title
                        current_section = line
                    
                    current_text += line + "\n"
                current_text += "\n"
        
        # Save any remaining text for the page
        if current_text.strip():
            extracted_data.append({
                "source_filename": os.path.basename(pdf_path),
                "page_number": page_num + 1,
                "section_title": current_section,
                "text": current_text.strip()
            })
            
    return extracted_data

def process_pdfs(raw_dir, processed_dir):
    raw_path = Path(raw_dir)
    processed_path = Path(processed_dir)
    
    processed_path.mkdir(parents=True, exist_ok=True)
    
    pdf_files = list(raw_path.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {raw_dir}")
        return
        
    for pdf_file in pdf_files:
        print(f"Processing {pdf_file.name}...")
        try:
            document_data = extract_metadata_and_text(pdf_file)
            
            # Save to JSON
            output_filename = pdf_file.stem + ".json"
            output_file = processed_path / output_filename
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, indent=4, ensure_ascii=False)
                
            print(f"Saved extracted data to {output_file}")
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {e}")

if __name__ == "__main__":
    RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
    PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
    
    # Ensure raw directory exists so user can place files there
    os.makedirs(RAW_DIR, exist_ok=True)
    
    if len(sys.argv) > 1:
        target_file = Path(RAW_DIR) / sys.argv[1]
        print(f"Processing {target_file.name}...")
        try:
            document_data = extract_metadata_and_text(target_file)
            output_file = Path(PROCESSED_DIR) / (target_file.stem + ".json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, indent=4, ensure_ascii=False)
            print(f"Saved extracted data to {output_file}")
        except Exception as e:
            print(f"Error processing {target_file.name}: {e}")
    else:
        process_pdfs(RAW_DIR, PROCESSED_DIR)
