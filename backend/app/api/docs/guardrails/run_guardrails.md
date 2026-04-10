Runs guardrails on input text with a selected list of validators.

Behavior notes:
- Runtime validator format uses `on_fail`; config-style payloads with `on_fail_action` are accepted and normalized.
- `suppress_pass_logs=true` skips persisting pass-case validator logs.
- The endpoint always saves a `request_log` entry for the run.
- Validator logs are also saved; with `suppress_pass_logs=true`, only fail-case validator logs are persisted. Otherwise, all validator logs are added.
- For `ban_list`, `ban_list_id` can be resolved to `banned_words` from tenant ban list configs.
- For `topic_relevance`, `topic_relevance_config_id` is required and is resolved to `configuration` + `prompt_schema_version` from tenant topic relevance configs. Requires `OPENAI_API_KEY` to be configured; returns a validation failure with an explicit error if missing.
- For `llm_critic`, `OPENAI_API_KEY` must be configured; returns `success=false` with an explicit error if missing.
- For `llamaguard_7b`, `policies` accepts human-readable policy names (see table below). If omitted, all policies are enforced by default.

  | `policies` value            | Policy enforced                  |
  |-----------------------------|----------------------------------|
  | `no_violence_hate`          | No violence or hate speech       |
  | `no_sexual_content`         | No sexual content                |
  | `no_criminal_planning`      | No criminal planning             |
  | `no_guns_and_illegal_weapons` | No guns or illegal weapons     |
  | `no_illegal_drugs`          | No illegal drugs                 |
  | `no_encourage_self_harm`    | No encouragement of self-harm    |
- `rephrase_needed=true` means the system could not safely auto-fix the input/output and wants the user to retry with a rephrased query.
- When a validator with `on_fail=fix` has no programmatic fix (e.g. `profanity_free`), `safe_text` will be `""` and the response `metadata.reason` will explain which validator caused the empty output.

Failure behavior:
- `success=false` is returned when validation fails without a recoverable fix or an internal runtime error occurs.
- Common failures include invalid `request_id` format and validator errors without fallback output.

Side effects:
- Saves/updates `request_log` with request context and final response status/text.
- Saves `validator_log` entries for executed validators based on `suppress_pass_logs`.
