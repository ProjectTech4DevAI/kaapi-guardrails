Create a ban list for the tenant resolved from `X-API-KEY`.

This endpoint stores a domain-scoped list of banned words used by the `ban_list` validator.

## Authentication
Requires `X-API-KEY: <token>`.

## Endpoint
- Method: `POST`
- Path: `/guardrails/ban_lists/`

## Request Body
`BanListCreate` object with:
- `name` (`string`, required)
- `description` (`string`, required)
- `domain` (`string`, required)
- `is_public` (`bool`, optional, default: `false`)
- `banned_words` (`string[]`, required)

## Successful Response
Returns `APIResponse[BanListResponse]`.

## Failure Behavior
Common failure cases:
- Missing or invalid `X-API-KEY`
- Payload schema validation errors
