#!/usr/bin/env bash

set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVAL_DIR="$BACKEND_DIR/app/evaluation"

# Support passing env assignments as args, e.g.:
#   scripts/run_all_evaluations.sh BAN_LIST_WORDS="foo,bar"
for arg in "$@"; do
  if [[ "$arg" == *=* ]]; then
    export "$arg"
  fi
done

RUNNERS=(
  "$EVAL_DIR/lexical_slur/run.py"
  "$EVAL_DIR/pii/run.py"
  "$EVAL_DIR/gender_assumption_bias/run.py"
  "$EVAL_DIR/ban_list/run.py"
)

echo "Running validator evaluations..."
echo "Backend dir: $BACKEND_DIR"

for runner in "${RUNNERS[@]}"; do
  name="$(basename "$(dirname "$runner")")"
  echo ""
  echo "==> [$name] $runner"

  if [[ "$name" == "ban_list" ]]; then
    : "${BAN_LIST_WORDS:?BAN_LIST_WORDS must be set for ban_list evaluation (comma-separated)}"
  fi

  uv run python "$runner"
done

echo ""
echo "All validator evaluations completed."
