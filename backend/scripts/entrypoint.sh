#!/usr/bin/env bash
set -euo pipefail

echo "Starting FastAPI server..."
exec fastapi run --workers 4 app/main.py
