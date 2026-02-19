Fetches a single ban list by id for the tenant resolved from `X-API-KEY`.

Behavior notes:
- Tenant's scope is enforced from the API key context.

Common failure cases:
- Missing or invalid API key.
- Ban list not found in tenant's scope.
- Invalid id format.
