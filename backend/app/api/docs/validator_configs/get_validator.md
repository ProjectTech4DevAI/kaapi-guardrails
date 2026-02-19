Fetches a single validator configuration by id within an organization/project scope.

Response data is flattened and includes both base validator fields and validator-specific config fields.

Behavior notes:
- Scope is strictly enforced; a validator id outside the provided organization/project is treated as inaccessible.

Common failure cases:
- Validator not found.
- Validator exists but does not match the provided scope.
