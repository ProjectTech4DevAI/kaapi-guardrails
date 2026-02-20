#!/usr/bin/env bash

set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVAL_DIR="$BACKEND_DIR/app/evaluation"

RUNNERS=(
  "$EVAL_DIR/lexical_slur/run.py"
  "$EVAL_DIR/pii/run.py"
  "$EVAL_DIR/gender_assumption_bias/run.py"
)

echo "Running validator evaluations..."
echo "Backend dir: $BACKEND_DIR"

for runner in "${RUNNERS[@]}"; do
  name="$(basename "$(dirname "$runner")")"
  echo ""
  echo "==> [$name] $runner"
  uv run python "$runner"
done

echo ""
echo "All validator evaluations completed."
