Get a single validator configuration by id.

The validator must belong to the provided organization and project scope.

## Authentication
Requires `Authorization: Bearer <token>`.

## Endpoint
- Method: `GET`
- Path: `/guardrails/validators/configs/{id}`

## Path Parameters
- `id` (`UUID`, required)

## Query Parameters
- `organization_id` (`int`, required)
- `project_id` (`int`, required)

## Successful Response
Returns `APIResponse[ValidatorResponse]` with flattened validator data.

## Failure Behavior
Common failure cases:
- Validator not found
- Validator exists but does not match provided organization/project scope
