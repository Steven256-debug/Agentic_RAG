FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PORT=7860

WORKDIR /app

# Install system build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Create standard user with UID 1000 for Hugging Face Spaces & Render compatibility
RUN useradd -m -u 1000 user && \
    mkdir -p /app/data/raw /app/.cache && \
    chown -R user:user /app

COPY --chown=user:user . .

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache

EXPOSE 7860

CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-7860}"]
