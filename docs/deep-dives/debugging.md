# Debugging & Observability

How to understand what's happening inside your validation pipelines.

---

## Reading Validator Logs

Every request produces a `validator_log` row for each validator that ran. This is your primary debugging tool.

**Fetching logs via database:**

```sql
-- See all FAIL outcomes for a specific request
SELECT name, input, output, error, outcome
FROM validator_log
WHERE request_id = 'your-request-log-id'
ORDER BY inserted_at;
```

**What each column tells you:**

| Column | Description |
|--------|-------------|
| `name` | Which validator ran (e.g., `"pii_remover"`, `"uli_slur_match"`) |
| `input` | The text this validator received (after previous validators ran) |
| `output` | The text this validator produced (may be redacted/changed) |
| `error` | Human-readable reason for failure. `null` if passed |
| `outcome` | `PASS` or `FAIL` |

**Example FAIL log:**

```json
{
  "name": "nsfw_text",
  "input": "original text here",
  "output": null,
  "error": "NSFW content detected with confidence 0.87 (threshold: 0.80)",
  "outcome": "FAIL"
}
```

**Note:** Pass logs are suppressed by default. You'll only see `FAIL` entries unless you change `suppress_pass_logs` in the validation call.

---

## Tracing a Request End-to-End

### 1. Find the request log

```sql
SELECT id, request_id, status, request_text, response_text, inserted_at
FROM request_log
WHERE request_id = 'your-client-request-uuid'
   OR response_id = 'your-response-uuid';
```

The `id` column is the internal log UUID used to join with `validator_log`.

### 2. See each validator's outcome

```sql
SELECT name, outcome, error, input, output
FROM validator_log
WHERE request_id = (
    SELECT id FROM request_log WHERE request_id = 'your-client-request-uuid'
)
ORDER BY inserted_at;
```

### 3. Trace the text transformation

Each validator row shows `input` (what it received) and `output` (what it produced). You can trace exactly how the text changed at each step:

```
Step 1: pii_remover
  Input:  "Priya Sharma called 9876543210"
  Output: "[REDACTED_PERSON_1] called [REDACTED_PHONE_NUMBER_1]"
  Outcome: FAIL (fix applied)

Step 2: uli_slur_match
  Input:  "[REDACTED_PERSON_1] called [REDACTED_PHONE_NUMBER_1]"
  Output: "[REDACTED_PERSON_1] called [REDACTED_PHONE_NUMBER_1]"
  Outcome: PASS
```

---

## Common Failure Patterns

### "safe_text is null"

An `exception` on_fail fired. Look for a FAIL row in `validator_log`. The `error` field explains why.

### "rephrase_needed: true"

A `rephrase` on_fail fired. The `safe_text` contains the rephrase message instead of processed text. Check which validator triggered by looking for the FAIL row.

### "safe_text is empty string"

A `fix` on_fail fired, but the validator returned `fix_value=None`. This means the validator couldn't automatically correct the text. The pipeline still continued, but the text was cleared.

Check which validator produced this: look for the FAIL row where `output` is empty.

### "Pipeline completed but unsafe content still present"

The text passed all validators. Possible causes:
- Threshold is too high (content scored below the threshold)
- The violation was not covered by the validators you configured
- The validator doesn't handle this specific pattern (e.g., Hinglish slur not in database)

Replay the specific input with a lower threshold or additional validators.

---

## Replaying Failed Cases

To reproduce a specific failure, extract the original request and replay it with a different configuration:

```python
# Replay with a lower nsfw_text threshold
replay_request = {
    "request_id": str(uuid.uuid4()),
    "organization_id": 1,
    "project_id": 1,
    "input": original_input,  # from request_log.request_text
    "validators": [
        {
            "type": "nsfw_text",
            "threshold": 0.6,  # lower threshold to see if it now fires
            "on_fail": "exception"
        }
    ]
}
```

This is useful when:
- A user reported content that should have been blocked
- You're tuning thresholds and want to see what specific content looks like at different settings

---

## Debugging Topic Relevance

Topic relevance failures can be opaque because the LLM scoring is not deterministic. To understand why something was scored as off-topic:

1. Look at the `error` field in `validator_log` — it will contain the LLM's score
2. Read your topic config: `GET /api/v1/guardrails/topic_relevance_configs/{id}`
3. Consider whether the config is too narrow — try adding more example topics to the description
4. Test the specific input manually against your topic description

**Improving topic configs:**

Be specific about what IS in scope, and give examples:

```
Bad:  "This assistant is for healthcare questions."

Better: "This assistant helps users with symptoms, medications, preventive care,
         and general health information. Examples of in-scope questions: 'What
         are the symptoms of diabetes?', 'Is ibuprofen safe to take with blood
         pressure medication?', 'How often should I get a health checkup?'
         Out-of-scope: cooking, sports, technology, legal advice."
```

---

## Debugging PII Detection

If expected PII is not being redacted, check:

1. **Entity type not configured** — The entity type may not be in your `entity_types` list. Check which types you included.

2. **Threshold too high** — Presidio's confidence for this entity may be below your threshold. Try lowering `threshold` to `0.3` and see if it fires.

3. **Entity not in Presidio's supported types** — Some niche formats may not be recognized. Consider adding them to a `ban_list` as a pattern fallback.

4. **Language/script mismatch** — Presidio performs better on standard Latin-script text. For Devanagari or regional scripts, results may vary.

---

## Sentry Integration

Production errors are reported to Sentry (configured via `SENTRY_DSN` env var). When a validator throws an unexpected exception:

- The exception is captured in Sentry with full stack trace
- The request returns `success: false` with an error message
- The `request_log` entry is updated to `status: error`

Check Sentry for validator crashes, LLM API timeouts, and unexpected model behavior.

---

## Structured Log Output

The application logs structured request metadata. In production, pipe logs to your log aggregation system:

```
INFO  request_id=... validator=pii_remover outcome=FAIL error="PERSON detected..."
INFO  request_id=... validator=uli_slur_match outcome=PASS
INFO  request_id=... response_id=... status=success latency_ms=234
```

Filter by `outcome=FAIL` to review blocked requests. Filter by `status=error` to review crashes.
