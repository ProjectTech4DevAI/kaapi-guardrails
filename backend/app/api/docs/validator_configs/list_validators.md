List validator configurations for an organization and project.

Supports optional filtering by id, stage, and type.

## Authentication
Requires `Authorization: Bearer <token>`.

## Endpoint
- Method: `GET`
- Path: `/guardrails/validators/configs/`

## Query Parameters
- `organization_id` (`int`, required)
- `project_id` (`int`, required)
- `ids` (`UUID[]`, optional)
- `stage` (`input | output`, optional)
- `type` (`validator type enum`, optional)

## Successful Response
Returns `APIResponse[list[ValidatorResponse]]`.

Each item is flattened and includes:
- Base validator fields (`id`, `type`, `stage`, `on_fail_action`, `is_enabled`, timestamps, scope ids)
- Validator-specific config fields

## Failure Behavior
Common failure cases:
- Invalid query parameter format (for example malformed UUID in `ids`)
