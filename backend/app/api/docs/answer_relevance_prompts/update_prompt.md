Partially updates an answer relevance prompt config by id for the tenant resolved from `X-API-KEY`.

Behavior notes:
- Supports patch-style updates; omitted fields remain unchanged.
- Tenant scope is enforced from the API key context.
- If `prompt_template` is updated, it must still contain both `{query}` and `{answer}` placeholders.

Common failure cases:
- Missing or invalid API key.
- Prompt config not found in tenant's scope.
- Payload schema validation errors.
- Updated `prompt_template` is missing `{query}` or `{answer}` placeholder.
