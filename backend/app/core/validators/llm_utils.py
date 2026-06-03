from litellm import get_supported_openai_params

# Passed to litellm/OpenAI to force a strict JSON object response.
JSON_OBJECT_RESPONSE_FORMAT = {"type": "json_object"}


def supports_response_format(model: str) -> bool:
    """Return True if the given model supports the OpenAI ``response_format`` param.

    Falls back to False if litellm cannot resolve the model's capabilities.
    """
    try:
        return "response_format" in (get_supported_openai_params(model=model) or [])
    except Exception:
        return False
