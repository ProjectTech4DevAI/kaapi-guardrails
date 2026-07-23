Creates a ban list for the tenant resolved from the `X-ORGANIZATION-ID` / `X-PROJECT-ID` headers.

Behavior notes:
- Stores a domain-scoped list of banned words used by the `ban_list` validator.
- `is_public` defaults to `false` when omitted.

Common failure cases:
- Missing or invalid API key.
- Payload schema validation errors.
