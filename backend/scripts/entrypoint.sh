#!/usr/bin/env bash
set -euo pipefail

echo "Running Guardrails setup..."
./scripts/install_guardrails_from_hub.sh

echo "Starting FastAPI server..."
exec fastapi run --workers 4 app/main.py
