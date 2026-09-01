Lists LLM prompt configs for the tenant resolved from the `X-ORGANIZATION-ID` / `X-PROJECT-ID` headers.

Behavior notes:
- Returns configs scoped to the tenant's `organization_id` and `project_id`.
- Optionally filter by `validator_name` to retrieve configs for a specific validator.
- Supports pagination via `offset` and `limit`.
- `offset` defaults to `0`.
- `limit` is optional; when omitted, no limit is applied.
- Results are ordered by `created_at` ascending, then `id`.

Common failure cases:
- Missing or invalid API key.
- Invalid pagination values.
