Create a validator configuration scoped to an organization and project.

This endpoint stores both common validator fields and validator-specific config fields for later execution.

## Authentication
Requires `Authorization: Bearer <token>`.

## Endpoint
- Method: `POST`
- Path: `/guardrails/validators/configs/`

## Query Parameters
- `organization_id` (`int`, required)
- `project_id` (`int`, required)

## Request Body
`ValidatorCreate` object with:
- `type` (required)
- `stage` (required)
- `on_fail_action` (optional, default: `fix`)
- `is_enabled` (optional, default: `true`)
- Additional validator-specific configuration fields

## Successful Response
Returns `APIResponse[ValidatorResponse]` with flattened validator data.

## Failure Behavior
Common failure cases:
- Duplicate validator for the same `(organization_id, project_id, type, stage)` combination
- Invalid enum values or payload schema violations
