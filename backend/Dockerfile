FROM python:3.10

ENV PYTHONUNBUFFERED=1

WORKDIR /app/

# Install uv
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

# Place executables in the environment at the front of the path
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#using-the-environment
ENV PATH="/app/.venv/bin:$PATH"

# Compile bytecode
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
ENV UV_COMPILE_BYTECODE=1

# uv Cache
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#caching
ENV UV_LINK_MODE=copy

# Install dependencies
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

ARG SPACY_MODEL_WHEEL_URL="https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl"

ENV PYTHONPATH=/app
RUN apt-get update && apt-get install -y jq && rm -rf /var/lib/apt/lists/*

COPY ./scripts /app/scripts
RUN chmod +x /app/scripts/*.sh

COPY ./pyproject.toml ./uv.lock ./alembic.ini /app/

COPY ./app /app/app

# Sync the project
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

# Install pinned spaCy model in the final environment used at runtime.
RUN python -m pip install --no-deps "${SPACY_MODEL_WHEEL_URL}"

# Set HuggingFace cache directory
ENV HF_HOME=/app/hf_cache

# Pre-download HuggingFace model
RUN --mount=type=secret,id=HF_TOKEN \
    HF_TOKEN="$(cat /run/secrets/HF_TOKEN 2>/dev/null || true)" \
    /app/.venv/bin/python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
AutoTokenizer.from_pretrained('textdetox/xlmr-large-toxicity-classifier', cache_dir='/app/hf_cache'); \
AutoModelForSequenceClassification.from_pretrained('textdetox/xlmr-large-toxicity-classifier', cache_dir='/app/hf_cache')"

# Pre-install Guardrails hub validators so container startup is not blocked by downloads
RUN --mount=type=secret,id=GUARDRAILS_HUB_API_KEY \
    GUARDRAILS_HUB_API_KEY="$(cat /run/secrets/GUARDRAILS_HUB_API_KEY 2>/dev/null || true)" \
    ENABLE_METRICS="false" \
    ENABLE_REMOTE_INFERENCING="true" \
    /app/scripts/install_guardrails_from_hub.sh
    
# -------------------------------
# Entrypoint (runtime setup)
# -------------------------------
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
