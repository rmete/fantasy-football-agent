#!/bin/bash

# Run backend locally with visible browser
cd "$(dirname "$0")"

echo "🚀 Starting Fantasy Football Backend Locally (Visible Browser Mode)"
echo "=================================================="
echo ""
echo "✨ Browser will be VISIBLE - you'll see it in action!"
echo "⏱️  Slowed down to 500ms per action so you can watch"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Activate virtual environment and run
source venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
