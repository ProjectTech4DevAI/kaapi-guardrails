Update a validator configuration by id.

Supports partial updates for base fields and validator-specific config fields.

## Authentication
Requires `Authorization: Bearer <token>`.

## Endpoint
- Method: `PATCH`
- Path: `/guardrails/validators/configs/{id}`

## Path Parameters
- `id` (`UUID`, required)

## Query Parameters
- `organization_id` (`int`, required)
- `project_id` (`int`, required)

## Request Body
`ValidatorUpdate` object (all fields optional):
- `type`
- `stage`
- `on_fail_action`
- `is_enabled`

Additional validator-specific config fields are merged into existing config.

## Successful Response
Returns `APIResponse[ValidatorResponse]` with updated flattened data.

## Failure Behavior
Common failure cases:
- Validator not found for provided scope
- Duplicate validator constraint after update
- Invalid update payload
