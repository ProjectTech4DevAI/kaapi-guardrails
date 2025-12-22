#!/usr/bin/env bash
set -euo pipefail

: "${GUARDRAILS_HUB_API_KEY:?GUARDRAILS_HUB_API_KEY is required}"

ENABLE_METRICS="${ENABLE_METRICS:-false}"
ENABLE_REMOTE_INFERENCING="${ENABLE_REMOTE_INFERENCING:-false}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST_FILE="${1:-$BACKEND_DIR/app/core/validators/validators.json}"

if [[ ! -f "$MANIFEST_FILE" ]]; then
  echo "Validator manifest not found: $MANIFEST_FILE"
  exit 1
fi

#######################################
# Configure Guardrails (non-interactive)
#######################################

echo "Configuring Guardrails CLI..."

guardrails configure \
  --token "$GUARDRAILS_HUB_API_KEY" \
  $( [[ "$ENABLE_METRICS" == "true" ]] && echo "--enable-metrics" || echo "--disable-metrics" ) \
  $( [[ "$ENABLE_REMOTE_INFERENCING" == "true" ]] && echo "--enable-remote-inferencing" || echo "--disable-remote-inferencing" )


#######################################
# Install hub validators
#######################################

echo "Reading validator manifest: $MANIFEST_FILE"

# Extract all non-local sources
HUB_SOURCES=$(jq -r '
  .validators[]
  | select(.source != "local")
  | .source
' "$MANIFEST_FILE")

if [[ -z "$HUB_SOURCES" ]]; then
  echo "No hub validators to install."
  exit 0
fi

for SRC in $HUB_SOURCES; do
  echo "Installing Guardrails hub validator: $SRC"
  guardrails hub install "$SRC"
done

echo "All hub validators installed successfully."
