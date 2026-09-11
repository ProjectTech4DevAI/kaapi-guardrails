# Architecture Deep Dive

How the system is structured and how a request flows through it.

---

## High-Level Architecture

```
Client
  │
  │ POST /api/v1/guardrails/
  ▼
FastAPI Application (port 8001)
  │
  ├─ Authentication dependency (source IP + Bearer token -> tenant)
  │
  ├─ Config Resolution
  │    ├─ Fetch ban list words from DB (if ban_list_id provided)
  │    └─ Fetch topic config from DB (if topic_relevance_config_id provided)
  │
  ├─ Guard Building
  │    └─ Each ValidatorConfig.build() → guardrails Validator instance
  │
  ├─ Sequential Validation (guardrails-ai framework)
  │    ├─ Validator 1 → PassResult or FailResult
  │    ├─ Validator 2 → PassResult or FailResult
  │    └─ Validator N → PassResult or FailResult
  │
  ├─ Result Processing
  │    ├─ Extract safe_text from validated_output
  │    └─ Detect rephrase_needed (checks rephrase prefix)
  │
  └─ Audit Logging
       ├─ RequestLog (request + response metadata)
       └─ ValidatorLog (per-validator outcome)

PostgreSQL Database
  ├─ request_log
  ├─ validator_log
  ├─ ban_list / ban_list_item
  ├─ topic_relevance_config
  └─ validator_config
```

---

## Request Lifecycle

### 1. Request parsing

```
POST /api/v1/guardrails/
```

The request body is parsed into `GuardrailRequest`:

```python
class GuardrailRequest(BaseModel):
    request_id: UUID
    organization_id: int
    project_id: int
    input: str
    validators: list[ValidatorConfigItem]  # union type
```

`ValidatorConfigItem` is a discriminated union — the `type` field routes to the correct config class (`PIIRemoverConfig`, `LexicalSlurConfig`, etc.).

### 2. Config resolution

Some validators reference stored resources by ID. Before building the guard, the API fetches the actual data:

- **`ban_list_id`** → fetches the list of banned words from the database
- **`topic_relevance_config_id`** → fetches the topic description string

This is what allows ban lists and topic configs to be updated without code changes.

### 3. Guard building

```python
validators = [config.build() for config in validator_configs]
guard = Guard().use(*validators)
```

Each config's `build()` method instantiates the underlying `guardrails-ai` `Validator` object with the correct parameters and `on_fail` handler.

### 4. Sequential validation

```python
result = guard.validate(input_text)
```

The guardrails-ai framework runs each validator in order. The output of each validator becomes the input to the next. The framework tracks the full history of each step.

**What happens on failure:**

- `on_fail="fix"`: The `fix_value` from `FailResult` is passed to the next validator. Validation continues.
- `on_fail="exception"`: An exception is raised. The pipeline stops. `safe_text` will be `null`.
- `on_fail="rephrase"`: A fixed rephrase message is set as the output. Validation continues with that message.

### 5. Result processing

```python
if result.validated_output:
    safe_text = result.validated_output
    rephrase_needed = safe_text.startswith(REPHRASE_ON_FAIL_PREFIX)
else:
    safe_text = None  # exception fired
```

### 6. Audit logging

Two database writes happen regardless of outcome:

**`request_log`** — created at the start, updated at the end:
```
id, organization_id, project_id, request_id, response_id,
status (processing → success/error), request_text, response_text
```

**`validator_log`** — one row per validator that ran:
```
id, request_id, organization_id, project_id,
name (validator type), input, output, error, outcome (PASS/FAIL)
```

Pass logs are suppressed by default (`suppress_pass_logs=true`). Only failures are written unless you change this.

---

## Data Models

### Request/Response

```python
# Request
class GuardrailRequest:
    request_id: UUID
    organization_id: int
    project_id: int
    input: str
    validators: list[ValidatorConfigItem]

# Response
class GuardrailResponse:
    response_id: UUID
    rephrase_needed: bool
    safe_text: str | None
```

### ValidatorConfigItem (discriminated union)

The API accepts validators as a union type. The `type` field selects which config class to use:

```python
ValidatorConfigItem = (
    LexicalSlurSafetyValidatorConfig
    | PIIRemoverSafetyValidatorConfig
    | GenderAssumptionBiasSafetyValidatorConfig
    | BanListSafetyValidatorConfig
    | TopicRelevanceSafetyValidatorConfig
    | LLMCriticSafetyValidatorConfig
    | LlamaGuard7BSafetyValidatorConfig
    | NSFWTextSafetyValidatorConfig
    | ProfanityFreeSafetyValidatorConfig
)
```

---

## Database Schema

### `request_log`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal log ID |
| `organization_id` | int | Tenant identifier |
| `project_id` | int | Project identifier |
| `request_id` | UUID | Client-provided request ID |
| `response_id` | UUID | Generated response ID |
| `status` | enum | `processing`, `success`, `error` |
| `request_text` | text | Original input |
| `response_text` | text | Processed output |
| `inserted_at` | datetime | — |
| `updated_at` | datetime | — |

### `validator_log`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal log ID |
| `request_id` | UUID FK | Links to `request_log.id` |
| `organization_id` | int | Tenant identifier |
| `project_id` | int | Project identifier |
| `name` | str | Validator type (e.g., `"pii_remover"`) |
| `input` | text | Text before this validator |
| `output` | text | Text after this validator |
| `error` | text | Error message if failed |
| `outcome` | enum | `PASS`, `FAIL` |
| `inserted_at` | datetime | — |

---

## API Routes Overview

| Route | Method | Description |
|-------|--------|-------------|
| `/api/v1/guardrails/` | POST | Run a validation pipeline |
| `/api/v1/guardrails/` | GET | List all available validator types and schemas |
| `/api/v1/guardrails/validators/configs/` | POST | Create a stored validator config |
| `/api/v1/guardrails/validators/configs/` | GET | List stored validator configs |
| `/api/v1/guardrails/validators/configs/{id}` | GET/PATCH/DELETE | Manage a config |
| `/api/v1/guardrails/ban_lists/` | POST/GET | Create / list ban lists |
| `/api/v1/guardrails/ban_lists/{id}` | GET/PATCH/DELETE | Manage a ban list |
| `/api/v1/guardrails/topic_relevance_configs/` | POST/GET | Create / list topic configs |
| `/api/v1/guardrails/topic_relevance_configs/{id}` | GET/PATCH/DELETE | Manage a topic config |

---

## Authentication

Two auth schemes are used:

**Bearer token** (main guardrail endpoints):
- Set `AUTH_TOKEN` in `.env`
- Send as `Authorization: Bearer <token>`
- Validated against SHA-256 hash of the plaintext token

**Source IP allowlist** (all endpoints except health check):
- Caller must appear in `ALLOWED_IPS`; checked before the token
- Reads the real connection source, not `X-Forwarded-For`

**Tenant headers** (all endpoints except health check):
- `X-ORGANIZATION-ID` + `X-PROJECT-ID`, resolved by the Kaapi backend
- Scope every read and write; never taken from the query string or body

---

## Key Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AUTH_TOKEN` | Yes | Bearer token for main API |
| `OPENAI_API_KEY` | For LLM validators | Used by `topic_relevance` and `llm_critic` |
| `GUARDRAILS_HUB_API_KEY` | For hub validators | Required for `ban_list`, `llamaguard_7b`, `nsfw_text`, `profanity_free` |
| `POSTGRES_*` | Yes | Database connection settings |
| `ALLOWED_IPS` | Yes in production | Comma-separated source IPs allowed to call this service |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | FastAPI |
| ORM / data models | SQLModel + Pydantic v2 |
| Validator framework | guardrails-ai |
| PII detection | Microsoft Presidio |
| ML models | HuggingFace Transformers + PyTorch |
| LLM integration | OpenAI API via guardrails-ai / LiteLLM |
| Database | PostgreSQL + psycopg3 |
| Migrations | Alembic |
| Error tracking | Sentry |
| Package management | uv |
| Python version | 3.10–3.13 |
