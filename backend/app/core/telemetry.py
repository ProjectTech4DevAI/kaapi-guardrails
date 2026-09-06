"""Single home for all observability wiring: Sentry (errors/logs) + OTel (traces).

Spans are produced only by the auto-instrumentors below plus two manual sites:
the guardrails.validate span in the guardrails route and the traced litellm
completion wrapper in llm_utils. Do not add instrumentation elsewhere.
"""

import logging

import sentry_sdk
from fastapi import FastAPI
from guardrails.settings import settings as guardrails_settings
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from sentry_sdk.integrations.opentelemetry import SentryPropagator, SentrySpanProcessor

from app.core.config import settings

logger = logging.getLogger(__name__)

# Health checks are uptime noise, not traffic worth tracing.
EXCLUDED_URLS = "utils/health-check"


def _scrub_event(event: dict, hint: dict) -> dict:
    # Request bodies are end-user text (potential PII). The full payload is
    # already persisted in request_log.metadata; Sentry only needs the pointer.
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
    return event


def setup_telemetry(app: FastAPI) -> None:
    """Initialize Sentry + OpenTelemetry. Call once from main.py.

    No-op unless OTEL_ENABLED is set, without a SENTRY_DSN, or in the
    testing environment, so tests and local runs stay instrumentation-free.
    """
    if not settings.OTEL_ENABLED or not settings.SENTRY_DSN or settings.ENVIRONMENT == "testing":
        return

    sentry_sdk.init(
        dsn=str(settings.SENTRY_DSN),
        environment=settings.ENVIRONMENT,
        # Spans come exclusively from OTel; Sentry's own span creation is off.
        instrumenter="otel",
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
        # Guardrails input/output is end-user text; never attach request/response
        # bodies to error events or trace transactions.
        max_request_body_size="never",
        enable_logs=True,  # INFO+ log records are shipped to Sentry Logs
        before_send=_scrub_event,
    )

    # guardrails-ai emits its own "guard"/"step"/"call"/"<validator>.validate"
    # spans via the same global tracer; too granular for our traces.
    guardrails_settings.disable_tracing = True

    resource = Resource.create({SERVICE_NAME: settings.OTEL_SERVICE_NAME})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SentrySpanProcessor())
    trace.set_tracer_provider(provider)
    set_global_textmap(SentryPropagator())

    FastAPIInstrumentor.instrument_app(
        app, excluded_urls=EXCLUDED_URLS, exclude_spans=["receive", "send"]
    )
    HTTPXClientInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    # No SQLAlchemyInstrumentor: DB spans are noise, not useful here.
    LoggingInstrumentor().instrument(set_logging_format=False)

    logger.info("Telemetry initialized (environment=%s)", settings.ENVIRONMENT)
