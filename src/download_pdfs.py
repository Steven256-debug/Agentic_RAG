import os
import requests
from urllib.parse import urlparse

# A selection of publicly available regulatory PDFs
PDF_URLS = [
    # Payment Systems and Services Act 2019 (Act 987)
    "https://www.bog.gov.gh/wp-content/uploads/2019/08/Payment-Systems-and-Services-Act-2019-Act-987-.pdf",
    # GSMA Mobile Money Regulatory Index Methodology
    "https://www.gsma.com/mobilemoneymetrics/assets/data/MMRI_Methodology.pdf",
    # Bank of Ghana - Cyber and Information Security Directive
    "https://www.bog.gov.gh/wp-content/uploads/2019/12/Cyber-and-Information-Security-Directive.pdf"
]

def download_pdfs(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    for url in PDF_URLS:
        try:
            print(f"Downloading {url}...")
            # We use a User-Agent because some sites block default python-requests
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Extract filename from URL
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)
            if not filename.endswith('.pdf'):
                filename += ".pdf"
                
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            print(f"Successfully saved to {filepath}\n")
        except Exception as e:
            print(f"Failed to download {url}: {e}\n")

if __name__ == "__main__":
    RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
    download_pdfs(RAW_DIR)
