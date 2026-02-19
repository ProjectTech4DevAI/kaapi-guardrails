# API Usage Guide

This guide explains how to use the current API surface for:
- Health checks
- Validator configuration CRUD
- Runtime validator discovery
- Guardrail execution
- Ban list CRUD for multi-tenant projects

## Base URL and Version

All routes are mounted under:
- `/api/v1`

Example local base URL:
- `http://localhost:8001/api/v1`

## Authentication

This API currently uses two auth modes:

1. Bearer token auth (`Authorization: Bearer <plain-text-token>`)
   - Used by validator config and guardrails endpoints.
   - The server validates your plaintext bearer token against a SHA-256 digest stored in `AUTH_TOKEN`.
2. multi-tenant API key auth (`X-API-KEY: <token>`)
   - Used by ban list endpoints.
   - The API key is verified against `KAAPI_AUTH_URL` and resolves tenant scope (`organization_id`, `project_id`).

Notes:
- `GET /utils/health-check/` is public.

## Response Shape

All API responses use:

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
- `POST /api/v1/guardrails/validators/configs/?organization_id=1&project_id=101`

Example (PII input validator):

```bash
curl -X POST "http://localhost:8001/api/v1/guardrails/validators/configs/?organization_id=1&project_id=101" \
  -H "Authorization: Bearer <token>" \
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
- `GET /api/v1/guardrails/validators/configs/?organization_id=1&project_id=101`

Optional filters:
- `ids=<uuid>&ids=<uuid>`
- `stage=input|output`
- `type=uli_slur_match|pii_remover|gender_assumption_bias|ban_list`

Example:

```bash
curl -X GET "http://localhost:8001/api/v1/guardrails/validators/configs/?organization_id=1&project_id=101&stage=input" \
  -H "Authorization: Bearer <token>"
```

## 2.3 Get validator config by id

Endpoint:
- `GET /api/v1/guardrails/validators/configs/{id}?organization_id=1&project_id=101`

Example:

```bash
curl -X GET "http://localhost:8001/api/v1/guardrails/validators/configs/<validator_id>?organization_id=1&project_id=101" \
  -H "Authorization: Bearer <token>"
```

## 2.4 Update validator config

Endpoint:
- `PATCH /api/v1/guardrails/validators/configs/{id}?organization_id=1&project_id=101`

Example:

```bash
curl -X PATCH "http://localhost:8001/api/v1/guardrails/validators/configs/<validator_id>?organization_id=1&project_id=101" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "is_enabled": false,
    "threshold": 0.7
  }'
```

## 2.5 Delete validator config

Endpoint:
- `DELETE /api/v1/guardrails/validators/configs/{id}?organization_id=1&project_id=101`

Example:

```bash
curl -X DELETE "http://localhost:8001/api/v1/guardrails/validators/configs/<validator_id>?organization_id=1&project_id=101" \
  -H "Authorization: Bearer <token>"
```

## 3) Runtime Validator Discovery

Endpoint:
- `GET /api/v1/guardrails/`

Purpose:
- Returns all runtime validator `type` values and their JSON schemas.

Example:

```bash
curl -X GET "http://localhost:8001/api/v1/guardrails/" \
  -H "Authorization: Bearer <token>"
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

Example:

```bash
curl -X POST "http://localhost:8001/api/v1/guardrails/?suppress_pass_logs=true" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "2a6f6d5c-5b9f-4f6b-92e4-cf7d67f87932",
    "organization_id": 1,
    "project_id": 101,
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

These endpoints manage tenant-scoped ban lists and use `X-API-KEY` auth.

Base path:
- `/api/v1/guardrails/ban_lists`

## 5.1 Create ban list

Endpoint:
- `POST /api/v1/guardrails/ban_lists/`

Example:

```bash
curl -X POST "http://localhost:8001/api/v1/guardrails/ban_lists/" \
  -H "X-API-KEY: <api-key>" \
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
  -H "X-API-KEY: <api-key>"
```

## 5.3 Get ban list by id

Endpoint:
- `GET /api/v1/guardrails/ban_lists/{id}`

Example:

```bash
curl -X GET "http://localhost:8001/api/v1/guardrails/ban_lists/<ban_list_id>" \
  -H "X-API-KEY: <api-key>"
```

## 5.4 Update ban list

Endpoint:
- `PATCH /api/v1/guardrails/ban_lists/{id}`

Example:

```bash
curl -X PATCH "http://localhost:8001/api/v1/guardrails/ban_lists/<ban_list_id>" \
  -H "X-API-KEY: <api-key>" \
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
  -H "X-API-KEY: <api-key>"
```

## 6) End-to-End Usage Pattern

Recommended request flow:
1. Create/update validator configs via `/guardrails/validators/configs`.
2. List configs and select active validators for a project.
3. Send selected validators in `POST /guardrails/`.
4. Use `safe_text` as downstream text.
5. If `rephrase_needed=true`, ask user to rephrase.
6. For `ban_list` validators without inline `banned_words`, create/manage a ban list first and pass `ban_list_id`.

## 7) Common Errors

- `401 Missing Authorization header`
  - Add `Authorization: Bearer <token>`.
- `401 Invalid authorization token`
  - Verify plaintext token matches server-side hash.
- `401 Missing X-API-KEY header`
  - Add `X-API-KEY: <api-key>` for ban list endpoints.
- `401 Invalid API key`
  - Verify the API key is valid in the upstream Kaapi auth service.
- `Invalid request_id`
  - Ensure `request_id` is a valid UUID string.
- `Validator already exists for this type and stage`
  - Type+stage is unique per organization/project scope.
- `Validator not found`
  - Confirm `id`, `organization_id`, and `project_id` match.

## 8) Current Validator Types

From `validators.json`:
- `uli_slur_match`
- `pii_remover`
- `gender_assumption_bias`
- `ban_list`

Source of truth:
- `backend/app/core/validators/validators.json`
- `GET /api/v1/guardrails/` (runtime-discovered schemas/types)

See detailed configuration notes in:
- `backend/app/core/validators/README.md`
