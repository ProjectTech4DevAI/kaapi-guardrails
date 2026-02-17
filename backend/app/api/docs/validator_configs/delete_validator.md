Delete a validator configuration by id.

The validator must belong to the provided organization and project scope.

## Authentication
Requires `Authorization: Bearer <token>`.

## Endpoint
- Method: `DELETE`
- Path: `/guardrails/validators/configs/{id}`

## Path Parameters
- `id` (`UUID`, required)

## Query Parameters
- `organization_id` (`int`, required)
- `project_id` (`int`, required)

## Successful Response
Returns `APIResponse[dict]` with:
- `message`: `"Validator deleted successfully"`

## Failure Behavior
Common failure cases:
- Validator not found for provided scope
