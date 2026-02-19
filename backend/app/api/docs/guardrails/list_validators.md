Lists all available runtime validators and their JSON schemas.

Use this endpoint to discover supported validator `type` values and validator-specific config schema before calling guardrail execution.

Behavior notes:
- Success payload is a plain object (`{"validators": [...]}`), not the `APIResponse` wrapper.
- Validator entries include `type` (runtime identifier) and `config` (validator JSON schema).

Common failure cases:
- Internal schema extraction/parsing error for a validator model.
