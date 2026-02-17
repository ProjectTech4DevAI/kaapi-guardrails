List all available runtime validators and their JSON schemas.

Use this endpoint to discover supported validator `type` values and model-specific configuration fields needed to build valid payloads for guardrail execution.

## Authentication
Requires `Authorization: Bearer <token>`.

## Endpoint
- Method: `GET`
- Path: `/guardrails/`

## Request Parameters
No body or query parameters.

## Successful Response
Returns an object containing `validators`.

Each item includes:
- `type`: validator identifier
- `config`: full JSON schema for that validator model

## Failure Behavior
Returns `APIResponse` failure when schema extraction fails for any validator model.

Common failure case:
- Internal schema generation/parsing error for a validator model
