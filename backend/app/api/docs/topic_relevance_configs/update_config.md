Partially updates a topic relevance configuration by id for the tenant resolved from `X-API-KEY`.

Behavior notes:
- Supports patch-style updates; omitted fields remain unchanged.
- `configuration` should be provided as a plain text scope sub-prompt (string).
- Tenant scope is enforced from the API key context.
- Duplicate configurations are rejected.

Common failure cases:
- Missing or invalid API key.
- Topic relevance preset not found in tenant's scope.
- Payload schema validation errors.
- Topic relevance with the same configuration already exists.
