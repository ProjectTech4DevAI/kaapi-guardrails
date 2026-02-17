Run guardrails on input text with a selected list of validators.

This endpoint evaluates unsafe content and returns a normalized API response with validated text and metadata needed by clients.

## Authentication
Requires `Authorization: Bearer <token>`.

## Endpoint
- Method: `POST`
- Path: `/guardrails/`

## Query Parameters
- `suppress_pass_logs` (`bool`, optional, default: `true`)
  - When `true`, passing validator results are not persisted in validator logs.

## Request Body
- `request_id` (`string`, required)
  - Must be a valid UUID string.
- `input` (`string`, required)
  - Raw user text to validate.
- `validators` (`array`, required)
  - Validator configuration objects.
  - Runtime format uses `on_fail`; config API format using `on_fail_action` is also accepted and normalized.
  - Supported validator `type` values are discovered from configured validator models.

## Successful Response
Returns `APIResponse[GuardrailResponse]`.

- `success`: `true`
- `data.response_id`: generated UUID for this validation response
- `data.rephrase_needed`: `true` when output starts with the rephrase marker
- `data.safe_text`: validated or transformed text

## Failure Behavior
Returns `APIResponse[GuardrailResponse]` with `success: false` when validation fails without a fix or runtime errors occur.

Common failure cases:
- Invalid `request_id` format
- Validator failure with no recoverable output
- Unexpected internal validation/runtime error

## Side Effects
- Creates a request log entry
- Updates request log with final status and response text
- Persists validator logs when available (subject to `suppress_pass_logs`)
