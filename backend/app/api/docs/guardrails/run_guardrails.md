Runs guardrails on input text with a selected list of validators.

Behavior notes:
- Runtime validator format uses `on_fail`; config-style payloads with `on_fail_action` are accepted and normalized.
- `suppress_pass_logs=true` skips persisting pass-case validator logs.
- The endpoint always saves a `request_log` entry for the run.
- Validator logs are also saved; with `suppress_pass_logs=true`, only fail-case validator logs are persisted. Otherwise, all validator logs are added.
- `rephrase_needed=true` means the system could not safely auto-fix the input/output and wants the user to retry with a rephrased query.
- When `rephrase_needed=true`, `safe_text` contains the rephrase prompt shown to the user.

Failure behavior:
- `success=false` is returned when validation fails without a recoverable fix or an internal runtime error occurs.
- Common failures include invalid `request_id` format and validator errors without fallback output.

Side effects:
- Saves/updates `request_log` with request context and final response status/text.
- Saves `validator_log` entries for executed validators based on `suppress_pass_logs`.
