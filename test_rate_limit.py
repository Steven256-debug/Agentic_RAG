import os
from google import genai
import time

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

try:
    print("Sending request...")
    response = client.models.embed_content(
        model='gemini-embedding-2',
        contents=["test text"] * 100,
    )
    print("Success:", len(response.embeddings))
except Exception as e:
    print("Error:", e)
