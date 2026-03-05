Creates a topic relevance configuration for the tenant resolved from `X-API-KEY`.

Behavior notes:
- Stores a topic relevance preset with `name`, `prompt_version`, and `configuration`.
- `configuration` is a plain text scope sub-prompt (string).
- Tenant scope is enforced from the API key context.
- Duplicate configurations are rejected.

Common failure cases:
- Missing or invalid API key.
- Payload schema validation errors.
- Topic relevance with the same configuration already exists.
