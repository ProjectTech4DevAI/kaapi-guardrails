Partially updates a ban list by id for the tenant resolved from the `X-ORGANIZATION-ID` / `X-PROJECT-ID` headers.

Behavior notes:
- Supports patch-style updates; omitted fields remain unchanged.
- Tenant's scope is enforced from the API key context.

Common failure cases:
- Missing or invalid API key.
- Ban list not found in tenant's scope.
- Payload schema validation errors.
