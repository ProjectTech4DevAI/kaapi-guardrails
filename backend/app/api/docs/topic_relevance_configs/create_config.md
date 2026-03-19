Creates a topic relevance configuration for the tenant resolved from `X-API-KEY`.

Behavior notes:
- Stores a topic relevance preset with `name`, `prompt_schema_version`, and `configuration`.
- `configuration` is a plain text scope sub-prompt (string).
- Tenant scope is enforced from the API key context.
- Duplicate configurations are rejected.

Common failure cases:
- Missing or invalid API key.
- Payload schema validation errors.
- Topic relevance with the same configuration already exists.

## Field glossary

**`configuration`**
A plain text string describing the topic scope the assistant is allowed to handle. This is injected into the LLM critic evaluation prompt at the `{{TOPIC_CONFIGURATION}}` placeholder to define what is considered in-scope.

Example:
```
This assistant only answers questions about maternal health and pregnancy care for NGO beneficiaries. It should not respond to questions about politics, general medicine unrelated to pregnancy, or financial topics.
```

**`prompt_schema_version`**
An integer selecting the versioned prompt template used to evaluate scope violations (e.g., `1` → `v1.md`). Controls the structure and wording of the LLM critic assessment prompt. Defaults to `1`. Only increment this when a new prompt template version has been added to the system.

Example: `1`
