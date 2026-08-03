#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GUARDRAILS_HUB_API_KEY="${GUARDRAILS_HUB_API_KEY:-}"

ENABLE_METRICS="${ENABLE_METRICS:-false}"
ENABLE_REMOTE_INFERENCING="${ENABLE_REMOTE_INFERENCING:-true}"

BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MANIFEST_FILE="${1:-$BACKEND_DIR/app/core/validators/validators.json}"

if [[ ! -f "$MANIFEST_FILE" ]]; then
  echo "Validator manifest not found: $MANIFEST_FILE"
  exit 1
fi

retry() {
  local attempts="$1"
  shift
  local delay=5
  local n=1

  until "$@"; do
    if (( n >= attempts )); then
      return 1
    fi
    echo "Attempt ${n}/${attempts} failed; retrying in ${delay}s..."
    sleep "$delay"
    n=$(( n + 1 ))
    delay=$(( delay * 2 ))
  done
}

#######################################
# Configure Guardrails (non-interactive)
#######################################

if [[ -n "$GUARDRAILS_HUB_API_KEY" ]]; then
  echo "Writing Guardrails configuration..."

  ANON_ID="$( { python3 -c 'import uuid; print(uuid.uuid4())' \
    || python -c 'import uuid; print(uuid.uuid4())'; } 2>/dev/null \
    || echo "00000000-0000-0000-0000-000000000000")"

  cat > "${HOME}/.guardrailsrc" <<EOF
id=${ANON_ID}
token=${GUARDRAILS_HUB_API_KEY}
enable_metrics=$( [[ "$ENABLE_METRICS" == "true" ]] && echo true || echo false )
use_remote_inferencing=$( [[ "$ENABLE_REMOTE_INFERENCING" == "true" ]] && echo true || echo false )
EOF
  chmod 600 "${HOME}/.guardrailsrc"
else
  echo "GUARDRAILS_HUB_API_KEY is not set; skipping Guardrails configuration."
fi


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
  if ! retry 4 guardrails hub install "$SRC"; then
    if [[ -z "$GUARDRAILS_HUB_API_KEY" ]]; then
      echo "Skipping hub validator install for $SRC because GUARDRAILS_HUB_API_KEY is not set."
      continue
    fi
    echo "Failed to install validator from Hub: $SRC"
    exit 1
  fi
done

echo "All hub validators installed successfully."
