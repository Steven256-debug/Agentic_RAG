import time
from sentence_transformers import SentenceTransformer

start = time.time()
print("Loading model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
print(f"Loaded in {time.time() - start:.2f}s")

texts = ["This is a test sentence."] * 100
start = time.time()
embs = model.encode(texts)
print(f"Encoded 100 chunks in {time.time() - start:.2f}s")
