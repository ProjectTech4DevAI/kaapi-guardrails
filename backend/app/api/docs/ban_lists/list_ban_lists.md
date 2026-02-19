Lists ban lists for the tenant resolved from `X-API-KEY`.

Behavior notes:
- Supports filtering by `domain`.
- Supports pagination via `offset` and `limit`.
- `offset` defaults to `0`.
- `limit` is optional; when omitted, no limit is applied.

Common failure cases:
- Missing or invalid API key.
- Invalid filter/pagination values.
