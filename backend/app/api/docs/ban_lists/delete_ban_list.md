Delete a ban list by id for the tenant resolved from `X-API-KEY`.

Only owner scope is allowed to delete the resource.

## Authentication
Requires `X-API-KEY: <token>`.

## Endpoint
- Method: `DELETE`
- Path: `/guardrails/ban_lists/{id}`

## Path Parameters
- `id` (`UUID`, required)

## Successful Response
Returns `APIResponse[dict]` with:
- `message`: `"Ban list deleted successfully"`

## Failure Behavior
Common failure cases:
- Missing or invalid `X-API-KEY`
- Ban list not found for the tenant scope
