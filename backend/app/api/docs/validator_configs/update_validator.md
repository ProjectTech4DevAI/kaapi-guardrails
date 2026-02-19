Partially updates a validator configuration by id within an organization/project scope.

Behavior notes:
- Supports patching base fields and validator-specific config fields.
- Validator-specific updates are merged into the existing config rather than replacing the entire config object.
- Omitted fields remain unchanged.
- Updates still honor uniqueness on `(organization_id, project_id, type, stage)`.

Common failure cases:
- Validator not found for provided scope.
- Duplicate validator conflict after changing `type`/`stage`.
- Invalid patch payload.
