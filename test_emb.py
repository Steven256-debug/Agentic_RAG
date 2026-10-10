import os
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
response = client.models.embed_content(
    model='text-embedding-004',
    contents=["hello", "world"]
)

for emb in response.embeddings:
    print(type(emb.values), len(emb.values))
