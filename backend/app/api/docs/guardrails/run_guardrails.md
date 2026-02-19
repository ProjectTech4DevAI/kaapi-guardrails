Runs guardrails on input text with a selected list of validators.

Behavior notes:
- Runtime validator format uses `on_fail`; config-style payloads with `on_fail_action` are accepted and normalized.
- `suppress_pass_logs=true` skips persisting pass-case validator logs.
- `rephrase_needed=true` means the system could not safely auto-fix the input/output and wants the user to retry with a rephrased query.
- When `rephrase_needed=true`, `safe_text` contains the rephrase prompt shown to the user.

Failure behavior:
- `success=false` is returned when validation fails without a recoverable fix or an internal runtime error occurs.
- Common failures include invalid `request_id` format and validator errors without fallback output.

Side effects:
- Creates and updates request logs for the run.
- Persists validator logs when available (subject to `suppress_pass_logs`).
