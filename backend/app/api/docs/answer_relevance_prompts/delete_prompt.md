Deletes an answer relevance prompt config by id for the tenant resolved from `X-API-KEY`.

Behavior notes:
- Tenant scope is enforced from the API key context.
- Deletion is permanent; any guardrail configs referencing this `custom_prompt_id` will fail to resolve at runtime after deletion.

Common failure cases:
- Missing or invalid API key.
- Prompt config not found in tenant's scope.
- Invalid id format.
