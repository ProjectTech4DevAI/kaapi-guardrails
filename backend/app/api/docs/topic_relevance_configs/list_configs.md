Lists topic relevance configurations for the tenant resolved from `X-API-KEY`.

Behavior notes:
- Supports pagination via `offset` and `limit`.
- `offset` defaults to `0`.
- `limit` is optional; when omitted, no limit is applied.
- Tenant scope is enforced from the API key context.

Common failure cases:
- Missing or invalid API key.
- Invalid pagination values.
