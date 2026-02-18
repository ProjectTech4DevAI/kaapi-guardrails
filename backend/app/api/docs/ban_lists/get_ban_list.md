Get a single ban list by id for the tenant resolved from `X-API-KEY`.

## Authentication
Requires `X-API-KEY: <token>`.

## Endpoint
- Method: `GET`
- Path: `/guardrails/ban_lists/{id}`

## Path Parameters
- `id` (`UUID`, required)

## Successful Response
Returns `APIResponse[BanListResponse]`.

## Failure Behavior
Common failure cases:
- Missing or invalid `X-API-KEY`
- Ban list not found for the tenant scope
- Invalid `id` format
