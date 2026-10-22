@echo off
echo Starting AI-powered sync...
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" auto_push.py
) else (
    python auto_push.py
)

