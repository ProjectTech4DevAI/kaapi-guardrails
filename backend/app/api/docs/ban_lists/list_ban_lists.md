List ban lists for the tenant resolved from `X-API-KEY`.

Supports optional filtering by `domain` and pagination.

## Authentication
Requires `X-API-KEY: <token>`.

## Endpoint
- Method: `GET`
- Path: `/guardrails/ban_lists/`

## Query Parameters
- `domain` (`string`, optional)
- `offset` (`int`, optional, default: `0`, min: `0`)
- `limit` (`int`, optional, min: `1`, max: `100`)

## Successful Response
Returns `APIResponse[list[BanListResponse]]`.

## Failure Behavior
Common failure cases:
- Missing or invalid `X-API-KEY`
- Invalid query parameter values
