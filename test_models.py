import os
from google import genai
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

for m in client.models.list():
    if "embed" in m.name.lower():
        print(m.name)
