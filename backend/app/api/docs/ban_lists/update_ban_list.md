Update a ban list by id for the tenant resolved from `X-API-KEY`.

Supports partial updates.

## Authentication
Requires `X-API-KEY: <token>`.

## Endpoint
- Method: `PATCH`
- Path: `/guardrails/ban_lists/{id}`

## Path Parameters
- `id` (`UUID`, required)

## Request Body
`BanListUpdate` object with optional fields:
- `name` (`string`, optional)
- `description` (`string`, optional)
- `domain` (`string`, optional)
- `is_public` (`bool`, optional)
- `banned_words` (`string[]`, optional)

## Successful Response
Returns `APIResponse[BanListResponse]`.

## Failure Behavior
Common failure cases:
- Missing or invalid `X-API-KEY`
- Ban list not found for the tenant scope
- Payload schema validation errors
