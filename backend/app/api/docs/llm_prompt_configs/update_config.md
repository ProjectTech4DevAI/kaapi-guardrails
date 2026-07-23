Partially updates an LLM prompt config by id for the tenant resolved from the `X-ORGANIZATION-ID` / `X-PROJECT-ID` headers.

Behavior notes:
- Supports patch-style updates; omitted fields remain unchanged.
- `validator_name` cannot be changed after creation.
- Tenant scope is enforced from the API key context.
- Duplicate configurations are rejected.

Common failure cases:
- Missing or invalid API key.
- LLM prompt config not found in tenant's scope.
- Payload schema validation errors.
- A config with the same configuration already exists.
