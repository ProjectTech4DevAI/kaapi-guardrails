#!/usr/bin/env bash

set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVAL_DIR="$BACKEND_DIR/app/evaluation"

RUNNERS=(
  "$EVAL_DIR/lexical_slur/run.py"
  "$EVAL_DIR/pii/run.py"
  "$EVAL_DIR/gender_assumption_bias/run.py"

  # Ban list evaluation with predefined words
  "$EVAL_DIR/ban_list/run.py:sonography,gender check"

  # Topic relevance evaluations
  "$EVAL_DIR/topic_relevance/run.py:education-topic-relevance-dataset.csv:education_topic_config.txt:education"
  "$EVAL_DIR/topic_relevance/run.py:healthcare-topic-relevance-dataset.csv:healthcare_topic_config.txt:healthcare"
)

echo "Running validator evaluations..."
echo "Backend dir: $BACKEND_DIR"

for runner in "${RUNNERS[@]}"; do
  IFS=':' read -r script_path arg1 arg2 arg3 <<< "$runner"

  # Topic relevance runner
  if [[ -n "${arg2:-}" && -n "${arg3:-}" ]]; then
    name="topic_relevance"

    echo ""
    echo "==> [$name] $script_path --domain $arg3"

    uv run python "$script_path" \
      --dataset "$arg1" \
      --topic-config "$arg2" \
      --domain "$arg3"

  # Ban list runner
  elif [[ -n "${arg1:-}" ]]; then
    name="ban_list"

    echo ""
    echo "==> [$name] $script_path --words \"$arg1\""

    uv run python "$script_path" \
      --words "$arg1"

  # Simple runner
  else
    name="$(basename "$(dirname "$script_path")")"

    echo ""
    echo "==> [$name] $script_path"

    uv run python "$script_path"
  fi
done

echo ""
echo "All validator evaluations completed."
