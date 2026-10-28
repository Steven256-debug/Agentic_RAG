FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=7860 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    VECLIB_MAXIMUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    TORCH_NUM_THREADS=1

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install lightweight CPU-only PyTorch first (reduces memory usage by >70% on Render 512MB)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Create standard user with UID 1000 for Hugging Face Spaces & Render compatibility
RUN useradd -m -u 1000 user && \
    mkdir -p /app/data/raw /app/.cache /home/user/.cache && \
    chown -R user:user /app /home/user

# Pre-cache SentenceTransformer model into image so it loads in <1s at runtime without network calls
ENV HF_HOME=/home/user/.cache
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" && \
    chown -R user:user /home/user/.cache

COPY --chown=user:user . .

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache

EXPOSE 7860

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1"]
