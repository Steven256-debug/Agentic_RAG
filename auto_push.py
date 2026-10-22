import os
import sys
import json
import subprocess
import urllib.request
import urllib.error

def load_env():
    """Lightweight, standard-library .env loader (no python-dotenv required)."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if k and k not in os.environ:
                os.environ[k] = v

def run_cmd(cmd):
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    stdout = result.stdout.strip() if result.stdout else ""
    stderr = result.stderr.strip() if result.stderr else ""
    return stdout, stderr, result.returncode

def generate_ai_commit_message(diff_text: str, api_key: str) -> str:
    """Calls Gemini REST endpoint using standard library urllib (no external packages required)."""
    prompt = (
        "Write a concise, single-line git commit message (max 10 words) that describes these code changes. "
        "IMPORTANT: You MUST write it strictly from a first-person perspective starting with 'I ' "
        "(for example: 'I added mobile responsiveness to the interface', 'I fixed a styling bug', 'I updated ComplyGH components'). "
        "Output ONLY the commit message itself without quotes, backticks, or extra explanation:\n\n"
        f"{diff_text[:4000]}"
    )
    
    model = os.getenv("FAST_MODEL", "gemini-2.5-flash-lite")
    # Clean model name if needed
    if model.startswith("models/"):
        model = model.replace("models/", "")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 60,
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=15) as resp:
        res_data = json.loads(resp.read().decode("utf-8"))
        candidates = res_data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts and "text" in parts[0]:
                text = parts[0]["text"].strip()
                cleaned = text.replace('"', '').replace("'", "").replace('`', '').replace('\n', ' ').strip()
                if not cleaned.lower().startswith("i "):
                    cleaned = f"I {cleaned[0].lower()}{cleaned[1:]}"
                return cleaned
    return "I updated ComplyGH with mobile responsive interface improvements"

def main():
    print("Staging files...")
    run_cmd("git add .")
    
    # Get the diff of what is staged
    stdout, stderr, code = run_cmd("git diff --cached")
    if not stdout:
        print("No changes to commit.")
        sys.exit(0)
        
    print("Analyzing changes to generate a first-person commit message...")
    load_env()
    api_key = os.environ.get("GEMINI_API_KEY")
    fallback_msg = "I updated ComplyGH with mobile responsive interface improvements"
    
    commit_msg = fallback_msg
    if not api_key:
        print("Note: GEMINI_API_KEY not found in .env. Using fallback message.")
    else:
        try:
            commit_msg = generate_ai_commit_message(stdout, api_key)
        except Exception as e:
            print(f"AI generation notice ({e}). Using rule-compliant fallback message.")
            commit_msg = fallback_msg
            
    print(f"Generated commit message: '{commit_msg}'")
    print("Committing...")
    run_cmd(f'git commit -m "{commit_msg}"')
    
    print("Pushing to GitHub...")
    stdout, stderr, code = run_cmd("git push origin main")
    if code != 0:
        print(f"Error pushing:\n{stderr}")
    else:
        print("Sync complete!")

if __name__ == "__main__":
    main()

