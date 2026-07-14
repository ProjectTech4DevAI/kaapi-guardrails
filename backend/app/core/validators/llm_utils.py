from litellm import get_supported_openai_params

# Passed to litellm/OpenAI to force a strict JSON object response.
JSON_OBJECT_RESPONSE_FORMAT = {"type": "json_object"}

# Models known to support JSON-object response_format that litellm may not list yet.
_KNOWN_JSON_CAPABLE_MODELS = frozenset(
    {
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-5-mini",
        "gpt-5.4-mini",
        "gpt-5.4-nano",
        "gpt-5-nano",
    }
)


def supports_response_format(model: str) -> bool:
    """Return True if the given model supports the OpenAI ``response_format`` param.

    Checks a static allowlist of known-capable models first (covers newly released
    models that litellm may not enumerate yet), then falls back to litellm.
    """
    model_id = model.split("/")[-1]  # strip optional provider prefix, e.g. "openai/"
    if model_id in _KNOWN_JSON_CAPABLE_MODELS:
        return True
    try:
        return "response_format" in (get_supported_openai_params(model=model) or [])
    except Exception:
        return False
