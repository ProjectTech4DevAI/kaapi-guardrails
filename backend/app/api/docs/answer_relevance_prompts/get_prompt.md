Fetches a single answer relevance prompt config by id for the tenant resolved from `X-API-KEY`.

Behavior notes:
- Tenant scope is enforced: only configs belonging to the resolved `organization_id` and `project_id` are accessible.

Common failure cases:
- Missing or invalid API key.
- Prompt config not found in tenant's scope.
- Invalid id format.
