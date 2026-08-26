from litellm import completion, get_supported_openai_params
from opentelemetry import trace

_tracer = trace.get_tracer(__name__)

# Passed to litellm/OpenAI to force a strict JSON object response.
JSON_OBJECT_RESPONSE_FORMAT = {"type": "json_object"}


def traced_completion(**kwargs):
    """litellm.completion wrapped in an OTel span with GenAI semantic attributes.

    The single choke point for LLM observability — validators import this
    (aliased as ``completion``) instead of instrumenting their own calls.
    """
    model = str(kwargs.get("model", "unknown"))
    with _tracer.start_as_current_span(
        f"chat {model}",
        attributes={
            "gen_ai.operation.name": "chat",
            "gen_ai.system": "litellm",
            "gen_ai.request.model": model,
        },
    ) as span:
        response = completion(**kwargs)
        response_model = getattr(response, "model", None)
        if response_model:
            span.set_attribute("gen_ai.response.model", response_model)
        usage = getattr(response, "usage", None)
        for attribute, field in (
            ("gen_ai.usage.input_tokens", "prompt_tokens"),
            ("gen_ai.usage.output_tokens", "completion_tokens"),
            ("gen_ai.usage.total_tokens", "total_tokens"),
        ):
            value = getattr(usage, field, None)
            if isinstance(value, int):
                span.set_attribute(attribute, value)
        return response


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
