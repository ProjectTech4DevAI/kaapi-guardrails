# API Usage Guide

This guide explains how to use the current API surface for:
- Health checks
- Validator configuration CRUD
- Runtime validator discovery
- Guardrail execution
- Ban list CRUD for multi-tenant projects
- LLM prompt config CRUD for multi-tenant projects (`topic_relevance` and `answer_relevance_custom_llm`)

## Base URL and Version

All routes are mounted under:
- `/api/v1`

Example local base URL:
- `http://localhost:8001/api/v1`

## Authentication

This service is internal. Its only caller is kaapi-backend, which authenticates the end user and
resolves the tenant before calling.

Every request must carry:

- `Authorization: Bearer <plain-text-token>` — validated against the SHA-256 digest in `AUTH_TOKEN`
- `X-ORGANIZATION-ID: <int>` and `X-PROJECT-ID: <int>` — the tenant, resolved by kaapi-backend
- and must arrive from an IP listed in `ALLOWED_IPS`

Tenant scope is never read from the query string or request body.

Notes:
- `GET /utils/health-check/` is public.

## Response Shape

All successful API responses use:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "metadata": null
}
```

Failure responses return `success: false` and an `error` message.

## 1) Health Check

Endpoint:
- `GET /api/v1/utils/health-check/`

Example:

```bash
curl -X GET "http://localhost:8001/api/v1/utils/health-check/"
```

Response:

```json
true
```

## 2) Validator Config APIs

These endpoints manage persisted validator configs scoped by:
- `organization_id`
- `project_id`

Base path:
- `/api/v1/guardrails/validators/configs`

## 2.1 Create validator config

Endpoint:
- `POST /api/v1/guardrails/validators/configs/`

Example (PII input validator):

```bash
curl -X POST "http://localhost:8001/api/v1/guardrails/validators/configs/" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "pii_remover",
    "stage": "input",
    "on_fail_action": "fix",
    "is_enabled": true,
    "entity_types": ["PERSON", "PHONE_NUMBER", "IN_AADHAAR"],
    "threshold": 0.6
  }'
```

## 2.2 List validator configs

Endpoint:
- `GET /api/v1/guardrails/validators/configs/`

Optional filters:
- `ids=<uuid>&ids=<uuid>`
- `stage=input|output`
- `type=uli_slur_match|pii_remover|gender_assumption_bias|ban_list|llm_critic|topic_relevance|llamaguard_7b|profanity_free|nsfw_text`
- `type=uli_slur_match|pii_remover|gender_assumption_bias|ban_list|llm_critic|topic_relevance|llamaguard_7b|profanity_free`

Example:

```bash
curl -X GET "http://localhost:8001/api/v1/guardrails/validators/configs/?stage=input" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101"
```

## 2.3 Get validator config by id

Endpoint:
- `GET /api/v1/guardrails/validators/configs/{id}`

Example:

```bash
curl -X GET "http://localhost:8001/api/v1/guardrails/validators/configs/<validator_id>" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101"
```

## 2.4 Update validator config

Endpoint:
- `PATCH /api/v1/guardrails/validators/configs/{id}`

Example:

```bash
curl -X PATCH "http://localhost:8001/api/v1/guardrails/validators/configs/<validator_id>" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101" \
  -H "Content-Type: application/json" \
  -d '{
    "is_enabled": false,
    "threshold": 0.7
  }'
```

## 2.5 Delete validator config

Endpoint:
- `DELETE /api/v1/guardrails/validators/configs/{id}`

Example:

```bash
curl -X DELETE "http://localhost:8001/api/v1/guardrails/validators/configs/<validator_id>" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101"
```

## 3) Runtime Validator Discovery

Endpoint:
- `GET /api/v1/guardrails/`

Purpose:
- Returns all runtime validator `type` values and their JSON schemas.

Example:

```bash
curl -X GET "http://localhost:8001/api/v1/guardrails/" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101"
```

## 4) Guardrail Execution

Endpoint:
- `POST /api/v1/guardrails/`

Query params:
- `suppress_pass_logs=true|false` (default `true`)

Request fields:
- `request_id` (UUID string)
- `organization_id` (int)
- `project_id` (int)
- `input` (text to validate)
- `validators` (runtime validator configs)

Important:
- Runtime validators use `on_fail`.
- If you pass objects from config APIs, server normalization supports `on_fail_action` and strips non-runtime fields.
- For `topic_relevance`, pass `topic_relevance_config_id` only. The API resolves `configuration` + `prompt_schema_version` in `guardrails.py` before validator execution.
- For `answer_relevance_custom_llm`, `input` must be a JSON string `{"query": "...", "answer": "..."}`. Pass `custom_prompt_id` to use a stored tenant prompt, or omit to use the built-in default prompt.

Example:

```bash
curl -X POST "http://localhost:8001/api/v1/guardrails/?suppress_pass_logs=true" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "2a6f6d5c-5b9f-4f6b-92e4-cf7d67f87932",
    "input": "Amit Gupta phone number is 919611188278",
    "validators": [
      {
        "type": "pii_remover",
        "on_fail": "fix",
        "entity_types": ["PERSON", "PHONE_NUMBER"],
        "threshold": 0.5
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

Possible success response:

```json
{
  "success": true,
  "data": {
    "response_id": "d676f841-4579-4b73-bf8f-fe968af842f1",
    "rephrase_needed": false,
    "safe_text": "[REDACTED_PERSON_1] phone number is [REDACTED_PHONE_NUMBER_1]"
  },
  "error": null,
  "metadata": null
}
```

When a validator with `on_fail=fix` has no programmatic fix (e.g. `profanity_free`), `safe_text` will be `""` and `metadata` will explain why:

```json
{
  "success": true,
  "data": {
    "response_id": "d676f841-4579-4b73-bf8f-fe968af842f1",
    "rephrase_needed": false,
    "safe_text": ""
  },
  "error": null,
  "metadata": {
    "reason": "Empty string has been returned since the validation failed for: profanity_free"
  }
}
```

Possible failure response:

```json
{
  "success": false,
  "data": {
    "response_id": "2f87665c-3e0f-4ea7-8d7d-2f97dfe8ec98",
    "rephrase_needed": true,
    "safe_text": "Please rephrase the query without unsafe content...."
  },
  "error": "Validation failed",
  "metadata": null
}
```

## 5) Ban List APIs (multi-tenant)

These endpoints manage tenant-scoped ban lists. The tenant comes from the `X-ORGANIZATION-ID` / `X-PROJECT-ID` headers.

Base path:
- `/api/v1/guardrails/ban_lists`

## 5.1 Create ban list

Endpoint:
- `POST /api/v1/guardrails/ban_lists/`

Example:

```bash
curl -X POST "http://localhost:8001/api/v1/guardrails/ban_lists/" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Safety Banned Terms",
    "description": "Terms not allowed for this tenant policy",
    "domain": "abuse",
    "is_public": false,
    "banned_words": ["slur_a", "slur_b"]
  }'
```

## 5.2 List ban lists

Endpoint:
- `GET /api/v1/guardrails/ban_lists/?domain=abuse&offset=0&limit=20`

Example:

```bash
curl -X GET "http://localhost:8001/api/v1/guardrails/ban_lists/?offset=0&limit=20" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101"
```

## 5.3 Get ban list by id

Endpoint:
- `GET /api/v1/guardrails/ban_lists/{id}`

Example:

```bash
curl -X GET "http://localhost:8001/api/v1/guardrails/ban_lists/<ban_list_id>" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101"
```

## 5.4 Update ban list

Endpoint:
- `PATCH /api/v1/guardrails/ban_lists/{id}`

Example:

```bash
curl -X PATCH "http://localhost:8001/api/v1/guardrails/ban_lists/<ban_list_id>" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated description",
    "banned_words": ["slur_a", "slur_b", "slur_c"]
  }'
```

## 5.5 Delete ban list

Endpoint:
- `DELETE /api/v1/guardrails/ban_lists/{id}`

Example:

```bash
curl -X DELETE "http://localhost:8001/api/v1/guardrails/ban_lists/<ban_list_id>" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101"
```

## 6) LLM Prompt Config APIs (multi-tenant)

These endpoints manage tenant-scoped LLM prompt configs for the `topic_relevance` and `answer_relevance_custom_llm` validators. The tenant comes from the `X-ORGANIZATION-ID` / `X-PROJECT-ID` headers.

Base path:
- `/api/v1/guardrails/llm_prompt_configs`

The `validator_name` field determines which validator the config applies to:
- `"topic_relevance"` — a scope description used as the LLM topic guard prompt. No placeholder requirements.
- `"answer_relevance_custom_llm"` — a custom evaluation prompt. Must contain `{query}` and `{answer}` placeholders.

## 6.1 Create LLM prompt config

Endpoint:
- `POST /api/v1/guardrails/llm_prompt_configs/`

Example (topic relevance):

```bash
curl -X POST "http://localhost:8001/api/v1/guardrails/llm_prompt_configs/" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101" \
  -H "Content-Type: application/json" \
  -d '{
    "validator_name": "topic_relevance",
    "name": "Maternal Health Scope",
    "description": "Topic guard for maternal health support bot",
    "prompt_schema_version": 1,
    "llm_prompt": "Pregnancy care: Questions about prenatal care, ANC visits, nutrition, supplements, danger signs. Postpartum care: Questions about recovery after delivery, breastfeeding, and mother health checks."
  }'
```

Example (answer relevance):

```bash
curl -X POST "http://localhost:8001/api/v1/guardrails/llm_prompt_configs/" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101" \
  -H "Content-Type: application/json" \
  -d '{
    "validator_name": "answer_relevance_custom_llm",
    "name": "Maternal Health Relevance",
    "description": "Checks if LLM answer addresses a maternal health query",
    "llm_prompt": "You are evaluating a maternal health assistant.\nQuery: {query}\nAnswer: {answer}\n\nDoes the answer directly address the maternal health query with accurate information?\nAnswer only YES or NO."
  }'
```

## 6.2 List LLM prompt configs

Endpoint:
- `GET /api/v1/guardrails/llm_prompt_configs/?offset=0&limit=20`

Optional filter:
- `validator_name=topic_relevance|answer_relevance_custom_llm`

Example:

```bash
curl -X GET "http://localhost:8001/api/v1/guardrails/llm_prompt_configs/?validator_name=topic_relevance&offset=0&limit=20" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101"
```

## 6.3 Get LLM prompt config by id

Endpoint:
- `GET /api/v1/guardrails/llm_prompt_configs/{id}`

Example:

```bash
curl -X GET "http://localhost:8001/api/v1/guardrails/llm_prompt_configs/<config_id>" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101"
```

## 6.4 Update LLM prompt config

Endpoint:
- `PATCH /api/v1/guardrails/llm_prompt_configs/{id}`

Example:

```bash
curl -X PATCH "http://localhost:8001/api/v1/guardrails/llm_prompt_configs/<config_id>" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101" \
  -H "Content-Type: application/json" \
  -d '{
    "llm_prompt": "Pregnancy care: Updated scope definition"
  }'
```

## 6.5 Delete LLM prompt config

Endpoint:
- `DELETE /api/v1/guardrails/llm_prompt_configs/{id}`

Example:

```bash
curl -X DELETE "http://localhost:8001/api/v1/guardrails/llm_prompt_configs/<config_id>" \
  -H "Authorization: Bearer <token>" \
  -H "X-ORGANIZATION-ID: 1" \
  -H "X-PROJECT-ID: 101"
```

## 8) End-to-End Usage Pattern

Recommended request flow:
1. Create/update validator configs via `/guardrails/validators/configs`.
2. List configs and select active validators for a project.
3. Send selected validators in `POST /guardrails/`.
4. Use `safe_text` as downstream text.
5. If `rephrase_needed=true`, ask user to rephrase.
6. For `ban_list` validators without inline `banned_words`, create/manage a ban list first and pass `ban_list_id`.
7. For `topic_relevance`, create/manage an LLM prompt config (`validator_name: "topic_relevance"`) and pass `topic_relevance_config_id` at runtime. The server resolves `llm_prompt` and `prompt_schema_version` internally.
8. For `answer_relevance_custom_llm`, format `input` as `{"query": "...", "answer": "..."}`. Optionally create an LLM prompt config (`validator_name: "answer_relevance_custom_llm"`) and pass `custom_prompt_id`. If no `custom_prompt_id` is given, the built-in default prompt is used.

## 9) Common Errors

- `401 Missing Authorization header`
  - Add `Authorization: Bearer <token>`.
- `401 Invalid authorization token`
  - Verify plaintext token matches server-side hash.
- `403 Forbidden`
  - Source IP is not in `ALLOWED_IPS`. Checked before the token.
- `422` on tenant headers
  - Add `X-ORGANIZATION-ID` and `X-PROJECT-ID`; both must be integers.
- `Invalid request_id`
  - Ensure `request_id` is a valid UUID string.
- `Validator already exists for this type and stage`
  - Type+stage is unique per organization/project scope.
- `Validator not found`
  - Confirm `id`, `organization_id`, and `project_id` match.
- `LLM prompt config not found`
  - Confirm the LLM prompt config `id` exists within your tenant scope.

## 10) Current Validator Types

From `validators.json`:
- `uli_slur_match`
- `pii_remover`
- `gender_assumption_bias`
- `ban_list`
- `llm_critic`
- `topic_relevance`
- `llamaguard_7b`
- `profanity_free`
- `nsfw_text`
- `answer_relevance_custom_llm`

Source of truth:
- `backend/app/core/validators/validators.json`
- `GET /api/v1/guardrails/` (runtime-discovered schemas/types)

See detailed configuration notes in:
- `backend/app/core/validators/README.md`
