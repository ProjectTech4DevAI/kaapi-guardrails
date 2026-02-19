Creates a validator configuration within an organization/project scope.

The record stores base validator metadata and validator-specific config fields in one object, then returns a flattened response shape.

Behavior notes:
- `on_fail_action` defaults to `fix` when omitted.
- `is_enabled` defaults to `true` when omitted.
- Uniqueness is enforced per `(organization_id, project_id, type, stage)`.

Common failure cases:
- Duplicate validator for the same `(organization_id, project_id, type, stage)` combination.
- Schema/enum validation errors in validator-specific config.
