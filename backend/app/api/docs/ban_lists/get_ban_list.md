Fetches a single ban list by id for the tenant resolved from the `X-ORGANIZATION-ID` / `X-PROJECT-ID` headers.

Behavior notes:
- Tenant's scope is enforced from the API key context.

Common failure cases:
- Missing or invalid API key.
- Ban list not found in tenant's scope.
- Invalid id format.
