# Kaapi Guardrails — Architecture Overview

## Purpose

Kaapi Guardrails is a standalone REST microservice that provides configurable safety validation for LLM-based applications. It sits between the caller (a chatbot, API gateway, etc.) and the LLM: the caller sends a piece of text through the guardrails service _before_ sending it to the LLM (input guardrail) and again _after_ receiving the LLM's reply (output guardrail), each time receiving a safe/unsafe verdict and optionally a redacted or rephrased version of the text.

The service is built on **FastAPI** + **SQLModel** + **PostgreSQL**, containerised with Docker, and delegates the core validation pipeline to the [guardrails-ai](https://github.com/guardrails-ai/guardrails) SDK (pinned to a specific commit of the upstream repo).

---

## High-Level Request Flow

```
Caller
  │
  │  POST /api/v1/guardrails/
  │  { request_id, organization_id, project_id, input, validators: [...] }
  ▼
FastAPI route  ──────────────────────────────────────────────
  │  1. Auth check (static bearer token or multitenant X-API-KEY)
  │  2. Write RequestLog (status=PROCESSING)
  │  3. Resolve config-backed validators
  │     ├── BanList  → fetch banned_words from DB
  │     └── TopicRelevance → fetch configuration + prompt_schema_version from DB
  │  4. build_guard(validators)   ← assembles a guardrails Guard
  │  5. guard.validate(input)
  │     ├─ PassResult  → status=SUCCESS, return safe_text
  │     ├─ FailResult  → status=ERROR,  return error_message
  │     └─ on_fail=FIX → status=SUCCESS, return redacted/fixed safe_text
  │  6. Write ValidatorLog per validator outcome
  │  7. Update RequestLog (status, response_text)
  ▼
APIResponse[GuardrailResponse]
  { response_id, rephrase_needed, safe_text }
```

---

## Component Map

```
backend/app/
├── main.py                        FastAPI app factory, middleware, Sentry
├── api/
│   ├── main.py                    APIRouter aggregator
│   ├── deps.py                    Auth & DB session dependencies
│   └── routes/
│       ├── guardrails.py          Core validation endpoint + logging logic
│       ├── validator_configs.py   CRUD for saved validator configs
│       ├── ban_lists.py           CRUD for ban-list word sets
│       ├── topic_relevance_configs.py  CRUD for topic-scope configs
│       └── utils.py               Health-check
├── core/
│   ├── guardrail_controller.py    build_guard() — wires ValidatorConfig → Guard
│   ├── on_fail_actions.py         rephrase_query_on_fail helper
│   ├── enum.py                    ValidatorType, Stage, GuardrailOnFail, …
│   ├── constants.py               String constants (prefixes, error messages)
│   ├── config.py                  Pydantic settings (env vars, file paths)
│   └── validators/
│       ├── pii_remover.py         Custom Presidio-backed validator
│       ├── lexical_slur.py        Custom regex/CSV-backed slur validator
│       ├── gender_assumption_bias.py  Custom CSV-backed bias validator
│       ├── topic_relevance.py     Custom LLMCritic-backed topic validator
│       ├── utils/files/
│       │   ├── curated_slurlist_hi_en.csv
│       │   └── gender_assumption_bias_words.csv
│       ├── prompts/topic_relevance/v1.md … v3.md
│       └── config/
│           ├── base_validator_config.py          BaseValidatorConfig
│           ├── pii_remover_safety_validator_config.py
│           ├── lexical_slur_safety_validator_config.py
│           ├── ban_list_safety_validator_config.py
│           ├── gender_assumption_bias_safety_validator_config.py
│           ├── topic_relevance_safety_validator_config.py
│           ├── llm_critic_safety_validator_config.py
│           ├── llamaguard_7b_safety_validator_config.py
│           ├── nsfw_text_safety_validator_config.py
│           └── profanity_free_safety_validator_config.py
├── models/
│   ├── config/
│   │   ├── validator_config.py    DB model — saved validator presets
│   │   ├── ban_list.py            DB model — named word-ban sets
│   │   └── topic_relevance.py     DB model — topic scope definitions
│   └── logging/
│       ├── request_log.py         DB model — one row per guardrail call
│       └── validator_log.py       DB model — one row per validator outcome
├── schemas/
│   └── guardrail_config.py        GuardrailRequest / GuardrailResponse / ValidatorConfigItem union
└── crud/                          Thin CRUD wrappers over SQLModel sessions
```

---

## The Guardrails-AI Integration

This service uses the [guardrails-ai Python SDK](https://github.com/guardrails-ai/guardrails) as its validation engine.

### Core SDK concepts used

| Concept | Role in this service |
|---|---|
| `Guard` | Assembled per-request by `build_guard()`. Holds an ordered list of validators and runs them in sequence via `guard.validate(text)`. |
| `Validator` | A callable that receives a string and returns `PassResult` or `FailResult`. Custom validators extend `Validator` and register with `@register_validator`. |
| `OnFailAction` | Enum: `EXCEPTION`, `FIX`, `NOOP`. Controls whether a failure raises, returns a fix value, or is silently noted. |
| `FailResult.fix_value` | The corrected/redacted string returned when `on_fail=FIX`. |
| `guard.history` | After `guard.validate()`, stores a `CallStack` with per-validator logs consumed by `add_validator_logs()`. |
| Guardrails Hub | Pre-built validators (`BanList`, `LLMCritic`, `LlamaGuard7B`, `NSFWText`, `ProfanityFree`) installed from `hub://guardrails/<name>`. |

### Guard assembly

```python
# guardrail_controller.py
def build_guard(validator_items):
    validators = [v_item.build() for v_item in validator_items]
    return Guard().use(*validators)
```

Each request carries a list of `ValidatorConfigItem` objects (a Pydantic discriminated union keyed on `type`). Each config's `.build()` method instantiates the concrete `Validator` with the caller-supplied parameters and the resolved `on_fail` handler.

---

## Validator Inventory

### Input guardrails (applied to the user's prompt before it reaches the LLM)

| Validator | Type key | Source | Description |
|---|---|---|---|
| **Lexical Slur** | `uli_slur_match` | Local (custom) | Detects slurs from a curated bilingual (Hindi/English) CSV. Normalises text (emoji removal, unicode NFKC, `ftfy` encoding fix) before matching. Supports severity filtering: `low`/`medium`/`high`/`all`. Redacts matches with `[REDACTED_SLUR]`. |
| **PII Remover** | `pii_remover` | Local (custom) | Uses Microsoft Presidio (`presidio_analyzer` + `presidio_anonymizer`) with a spaCy NLP engine (`en_core_web_lg`). Detects and redacts 15 entity types including India-specific identifiers (Aadhaar, PAN, Passport, Vehicle Registration, Voter ID). Replaces entities with labelled placeholders, e.g. `[REDACTED_PERSON_1]`. |
| **Ban List** | `ban_list` | Hub (`guardrails/ban_list`) | Blocks exact words from a caller-supplied list or a stored `BanList` DB record (referenced by UUID). Words are fetched from the database in `_resolve_validator_configs()` before the guard runs. |
| **Topic Relevance** | `topic_relevance` | Local (custom) | Wraps the Hub's `LLMCritic` validator. Given a freeform topic-scope description (stored as a `TopicRelevance` DB record or supplied inline), constructs a scoring prompt and calls an LLM (default: `gpt-4o-mini`) via LiteLLM. Scores 1–3; score ≤ 1 is a fail. Supports versioned prompt templates (`v1.md`–`v3.md`). |
| **Profanity Free** | `profanity_free` | Hub (`guardrails/profanity_free`) | Detects general profanity in text. |

### Output guardrails (applied to the LLM's reply before it is sent to the user)

| Validator | Type key | Source | Description |
|---|---|---|---|
| **Gender Assumption Bias** | `gender_assumption_bias` | Local (custom) | Detects gender-stereotyping words loaded from a CSV (columns: `word`, `neutral-term`, `type`). Supports domain-specific categories: `generic`, `healthcare`, `education`, or `all`. Replaces biased words with their neutral counterparts as the fix value. |
| **NSFW Text** | `nsfw_text` | Hub (`guardrails/nsfw_text`) | ML-based NSFW/toxicity classification using `textdetox/xlmr-large-toxicity-classifier` (XLM-RoBERTa large, runs on CPU). Configurable threshold (default 0.8) and validation method (`sentence`). |
| **LlamaGuard 7B** | `llamaguard_7b` | Hub (`guardrails/llamaguard_7b`) | Meta's LlamaGuard safety model. Checks against named policies: `no_violence_hate` (O1), `no_sexual_content` (O2), `no_criminal_planning` (O3), `no_guns_and_illegal_weapons` (O4), `no_illegal_drugs` (O5), `no_encourage_self_harm` (O6). Requires a Hugging Face token (`HF_TOKEN`). |
| **LLM Critic** | `llm_critic` | Hub (`guardrails/llm_critic`) | General-purpose LLM-as-judge. Evaluates output against caller-defined metrics (name → description + threshold). Used standalone for custom quality checks. Requires `OPENAI_API_KEY`. |

> The `stage` field (`input` / `output`) on stored `ValidatorConfig` records is metadata for the caller's orchestration layer. The guardrails service itself applies every validator in `validators` to the single `input` string passed in the request; the caller is responsible for calling the service at the right point in the LLM pipeline.

---

## On-Fail Behaviour

Each validator config carries an `on_fail` value (`fix`, `exception`, `rephrase`). `BaseValidatorConfig.resolve_on_fail()` translates this to a handler passed into the guardrails SDK:

| `on_fail` value | SDK behaviour | Response to caller |
|---|---|---|
| `fix` (default) | Validator returns `fix_value` from `FailResult` (redacted/corrected text). If no fix value is available, returns `""` and sets `_validator_metadata` with a reason. | `status=SUCCESS`, `safe_text=<fixed text>` |
| `exception` | Guardrails raises `ValidationError`; caught and translated to `_extract_error_from_guard`. | `status=ERROR`, error message in response |
| `rephrase` | Returns a string prefixed with `"Please rephrase the query without unsafe content."` (optionally with the error reason appended). The `rephrase_needed=True` flag is set in the response, signalling the caller to ask the user to rephrase. | `status=SUCCESS`, `rephrase_needed=true`, `safe_text=<rephrase prompt>` |

The `LLMCritic` validator has a special rephrase path: it returns a fixed `LLM_CRITIC_REPHRASE_MESSAGE` string without embedding the critic's error detail (to avoid confusing end users).

---

## Configuration Management

### Validator presets (`validator_config` table)

Named, per-project validator configurations that can be stored and referenced. Fields: `type`, `stage`, `on_fail_action`, `is_enabled`, and a JSONB `config` blob holding validator-specific parameters. The `GuardrailRequest` schema normalises incoming saved configs (stripping DB-only fields like `id`, `created_at`) before they reach the validation pipeline.

### Ban lists (`ban_list` table)

Named word-lists scoped to `organization_id` + `project_id`. A `BanListSafetyValidatorConfig` may reference one by UUID (`ban_list_id`) instead of embedding `banned_words` inline; the route resolves the words at request time.

### Topic relevance configs (`topic_relevance` table)

Named topic-scope definitions (a freeform text blob) paired with a `prompt_schema_version`. A `TopicRelevanceSafetyValidatorConfig` may reference one by UUID (`topic_relevance_config_id`); the route fetches the config text at request time.

---

## Observability & Logging

Every guardrails call produces two log rows in PostgreSQL:

**`request_log`** — one row per API call
- Tracks `request_id` (caller-supplied), `organization_id`, `project_id`, status (`PROCESSING` → `SUCCESS` / `ERROR`), `request_text`, `response_text`, timestamps.

**`validator_log`** — one row per validator outcome within a call
- Tracks `name` (validator type), `input`, `output` (post-validation value), `error` (fail message), `outcome` (`PASS` / `FAIL`), linked to `request_log` by foreign key.
- Pass results are suppressed by default (`suppress_pass_logs=True`) to reduce write volume; pass through `suppress_pass_logs=false` as a query param to log all outcomes.

Error messages are sanitised before persistence: the input string is redacted from error messages to avoid storing sensitive user data in logs (`_redact_input`).

---

## Authentication

Two auth modes coexist:

**Static bearer token** (`AuthDep`): a SHA-256 hex digest configured in `AUTH_TOKEN`. Used by the core guardrails route and config management routes. Compared with `secrets.compare_digest` to prevent timing attacks.

**Multitenant X-API-KEY** (`MultitenantAuthDep`): an API key resolved against an external Kaapi auth service (`KAAPI_AUTH_URL`). The auth service returns `organization_id` + `project_id`, enabling per-tenant data isolation. Accepts the key as `X-API-KEY` header, `Authorization: Bearer`, or `access_token` cookie.

---

## Infrastructure

| Component | Technology |
|---|---|
| Web framework | FastAPI (uvicorn) |
| ORM / schema | SQLModel (Pydantic v2 + SQLAlchemy) |
| Database | PostgreSQL (psycopg3) |
| Migrations | Alembic |
| Validation engine | guardrails-ai (pinned git commit) |
| NLP (PII) | spaCy `en_core_web_lg` via Presidio |
| ML (toxicity) | PyTorch CPU, `textdetox/xlmr-large-toxicity-classifier` via Transformers |
| LLM calls | LiteLLM (used internally by `LLMCritic` / `TopicRelevance`) |
| Package manager | uv |
| Containerisation | Docker Compose — `prestart` (migrations) + `backend` services |
| Error tracking | Sentry (`sentry-sdk[fastapi]`) |

---

## Extending with a New Validator

1. Implement `Validator` subclass in `backend/app/core/validators/<name>.py` using `@register_validator`.
2. Add a `BaseValidatorConfig` subclass in `backend/app/core/validators/config/<name>_safety_validator_config.py` with a `Literal["<type_key>"]` discriminator field and a `build()` method.
3. Add the new config class to the `ValidatorConfigItem` union in [backend/app/schemas/guardrail_config.py](../../backend/app/schemas/guardrail_config.py).
4. Add the new `ValidatorType` enum value in [backend/app/core/enum.py](../../backend/app/core/enum.py).
5. Register the validator in [backend/app/core/validators/validators.json](../../backend/app/core/validators/validators.json).
6. If the validator needs DB-resolved config, add a resolution branch in `_resolve_validator_configs()` in [backend/app/api/routes/guardrails.py](../../backend/app/api/routes/guardrails.py).
