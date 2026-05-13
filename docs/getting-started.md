# Getting Started

Get from zero to a running validation pipeline in under 5 minutes.

---

## What is Kaapi Guardrails?

Think of validators as automated reviewers that inspect user input or model output before it reaches production. You chain them together into a pipeline — the text passes through each validator in sequence, and each one can fix, block, or flag problems it finds.

**What it solves:**

- Toxic or abusive language reaching users
- PII (names, phone numbers, Aadhaar) leaking through LLM responses
- Biased or gendered language in AI outputs
- Jailbreaks and unsafe content
- Responses that drift off-topic
- Banned words slipping through

**Where it fits in your stack:**

```
User Input → [Guardrails Pipeline] → LLM → [Guardrails Pipeline] → User Response
                    ↓
            Validate, fix, block, or escalate
```

You can validate **inputs** (before the LLM sees them), **outputs** (before users see them), or both.

---

## Prerequisites

- Docker and Docker Compose
- `uv` for Python package management
- OpenAI API key (for LLM-based validators: `topic_relevance`, `llm_critic`)
- Guardrails Hub API key (for hub validators: `ban_list`, `llamaguard_7b`, `nsfw_text`, `profanity_free`)

---

## Installation

**1. Clone and configure:**

```bash
git clone <repo-url>
cd kaapi-guardrails
cp .env.example .env
```

**2. Edit `.env` with your keys:**

```env
AUTH_TOKEN=your-bearer-token-here
OPENAI_API_KEY=sk-...
GUARDRAILS_HUB_API_KEY=your-guardrails-hub-key
POSTGRES_USER=app
POSTGRES_PASSWORD=changethis
POSTGRES_DB=app
```

**3. Start the services:**

```bash
# First-time setup: run migrations and seed data
docker compose --profile prestart up prestart

# Then start in development mode
docker compose watch
```

The API is now available at `http://localhost:8001`.

---

## Your First Validation

Send a request with a PII validator to scrub personal information:

```bash
curl -X POST "http://localhost:8001/api/v1/guardrails/" \
  -H "Authorization: Bearer your-bearer-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "organization_id": 1,
    "project_id": 1,
    "input": "Please contact Priya Sharma at priya@example.com or call 9876543210",
    "validators": [
      {
        "type": "pii_remover",
        "on_fail": "fix"
      }
    ]
  }'
```

**Expected response:**

```json
{
  "success": true,
  "data": {
    "response_id": "d676f841-4579-4b73-bf8f-fe968af842f1",
    "rephrase_needed": false,
    "safe_text": "Please contact [REDACTED_PERSON_1] at [REDACTED_EMAIL_ADDRESS_1] or call [REDACTED_PHONE_NUMBER_1]"
  },
  "error": null
}
```

---

## Chaining Multiple Validators

Validators run in the order you specify. The output of each becomes the input to the next.

```bash
curl -X POST "http://localhost:8001/api/v1/guardrails/" \
  -H "Authorization: Bearer your-bearer-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "550e8400-e29b-41d4-a716-446655440001",
    "organization_id": 1,
    "project_id": 1,
    "input": "Amit Gupta is an idiot, his number is 919611188278",
    "validators": [
      {
        "type": "pii_remover",
        "on_fail": "fix",
        "entity_types": ["PERSON", "PHONE_NUMBER"]
      },
      {
        "type": "uli_slur_match",
        "on_fail": "fix",
        "languages": ["en", "hi"],
        "severity": "all"
      }
    ]
  }'
```

The text first has PII redacted, then is checked for slurs. Both fixes are applied.

---

## Understanding the Response

| Field | What it means |
|-------|--------------|
| `success` | `true` if the pipeline completed (even if validators triggered) |
| `safe_text` | The processed text after all validators ran. `null` if an `exception` on_fail fired |
| `rephrase_needed` | `true` if the `rephrase` on_fail action triggered — your app should prompt the user to rewrite their input |
| `error` | Set when `success: false` — describes what went wrong at the API level |

**When `safe_text` is null:** This happens when a validator is configured with `"on_fail": "exception"` and a violation is found. The pipeline stops and returns an error instead of a safe version of the text.

---

## Next Steps

- [Core Concepts](core-concepts.md) — understand how the pipeline works
- [All Validators](validators.md) — explore all 9 validators and their options
- [Pipeline Design Patterns](pipeline-patterns.md) — copy-paste pipelines for common scenarios
