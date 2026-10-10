import os
import sys
import subprocess
from dotenv import load_dotenv
from google import genai
from google.genai import types

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def main():
    print("Staging files...")
    run_cmd("git add .")
    
    # Get the diff of what is staged
    stdout, stderr, code = run_cmd("git diff --cached")
    if not stdout:
        print("No changes to commit.")
        sys.exit(0)
        
    print("Analyzing changes to generate a commit message...")
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env. Using fallback message.")
        commit_msg = "Auto-generated sync"
    else:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"Write a concise, single-line git commit message (max 10 words) that describes these code changes. Do not include quotes or any extra text, just the message itself:\n\n{stdout[:5000]}"
            
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )
            commit_msg = response.text.strip().replace('"', '').replace('\n', ' ')
        except Exception as e:
            print(f"AI generation failed: {e}. Using fallback message.")
            commit_msg = "Auto-generated sync"
            
    print(f"Generated message: '{commit_msg}'")
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
