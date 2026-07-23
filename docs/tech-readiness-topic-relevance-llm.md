# Tech Readiness — API surface

Review of `backend/app/api/*` and its direct dependencies. Each finding has a
location, what's wrong, and the fix. Ordered by severity so you can take them one
by one. Auth model is assumed to stay as-is (X-API-KEY for the config endpoints,
static token for guardrails and validator configs).

---

## Blockers

### 1. Static token can reach any tenant

`routes/guardrails.py:49-80` and `routes/validator_configs.py:22-112` use `AuthDep` —
one server-wide token (`deps.py:40-58`) — but read `organization_id` / `project_id`
from the query or body. Anyone with the token can read or change any tenant's data.

Fix: move both routers to `MultitenantAuthDep` and drop the caller-supplied tenant
fields. Until then, treat it as an accepted risk with an owner and a date.

### 2. `bool` passes as a tenant id

`deps.py:100` checks `isinstance(x, int)`. In Python `bool` is an `int`, so if the
auth backend returns `"organization_id": true`, it resolves to tenant 1.

Fix: also reject `bool`.
```python
if not isinstance(x, int) or isinstance(x, bool):
    raise _unauthorized("Invalid credentials")
```

### 3. `topic_relevance_llm` missing from the LLM validator enum

`LLMValidatorName` (`core/enum.py:4-6`) has only `topic_relevance` and
`answer_relevance_custom_llm`. The create schema (`schemas/llm_prompt_config.py:47`)
and the list filter (`routes/llm_prompt_configs.py:49`) are typed to this enum, so
`topic_relevance_llm` is rejected with "validator not supported".

Fix: add the value. The router and CRUD are already validator-agnostic, so this alone
enables create, list, get, patch, and delete.
```python
class LLMValidatorName(str, Enum):
    TopicRelevance = "topic_relevance"
    TopicRelevanceLLM = "topic_relevance_llm"   # new
    AnswerRelevanceCustomLLM = "answer_relevance_custom_llm"
```

### 4. Runtime binds the wrong config type

`routes/guardrails.py:148` accepts a `topic_relevance` config for both topic
validators. After fix 3, a `topic_relevance_llm` validator could pull a
`topic_relevance` config, or the reverse.

Fix: bind each validator to its own config name.
```python
expected = (
    LLMValidatorName.TopicRelevanceLLM
    if isinstance(validator, TopicRelevanceLLMSafetyValidatorConfig)
    else LLMValidatorName.TopicRelevance
)
if config.validator_name != expected:
    raise HTTPException(400, f"Config '{config.id}' is for '{config.validator_name}', not '{expected.value}'")
```

### 5. `ValidatorUpdate` can corrupt a stored config

`schemas/validator_config.py:24-31` lets a PATCH change `type`, but
`crud/validator_config.py:97-120` merges the old config JSON on top of the new type.
A `pii_remover` PATCHed to `ban_list` keeps stale PII keys.

Fix: forbid changing `type` in PATCH, or clear `config` when `type` changes.

---

## Should fix

### 6. Whole chain runs against output data

`routes/guardrails.py:68-72`: if any validator is `answer_relevance_custom_llm`, the
entire chain runs against `payload.output`. A mixed chain (input validator + output
validator) runs the input validators against the wrong data.

Fix: split validators by stage and run each against its own data.

### 7. Request log orphaned when resolution or create fails

`routes/guardrails.py:63-67` creates the request log before `_resolve_validator_configs`.
Any error during resolution (or a DB error other than `ValueError` in `create`) leaves an
unfinished row. Fix 4 adds another raise here.

Fix: wrap resolution and create so failures finalize the log with an error status.

### 8. `prompt_schema_version` dropped for the LLM topic validator

`TopicRelevanceLLMSafetyValidatorConfig` has a `prompt_schema_version` field
(`core/validators/config/topic_relevance_llm_safety_validator_config.py:15`), but
`routes/guardrails.py:155-157` only copies it onto the non-LLM variant. A stored version
on a `topic_relevance_llm` config is ignored.

Fix: set it for the LLM variant too and fix the stale comment. If versioning isn't meant
to apply here, say so instead of dropping it silently.

### 9. Blocking, uncached auth call per request

`deps.py:76-85`: every multitenant request makes a blocking `httpx.get` to
`KAAPI_AUTH_URL`, using a threadpool worker each time.

Fix: add an in-process TTL cache keyed on the credential hash; make the dep async.

### 10. Only the first validator's metadata is returned

`routes/guardrails.py:244-247` returns `next(...)`, so later validators' metadata is
dropped in a chain.

Fix: aggregate metadata into a per-validator map.

### 11. Auth call has no retry and one shared timeout

`deps.py:79`: a single `timeout` covers all phases, and there's no retry.

Fix: split connect and read timeouts; add one bounded retry on network error.

### 12. PATCH can't change type-specific fields

`ValidatorBase` allows extra fields, `ValidatorUpdate` forbids them
(`schemas/validator_config.py:11,25`). So PATCH can't update any type-specific field.

Fix: allow extras on update, or expose a dedicated config dict.

### 13. Docs don't cover errors or versioning

`API_USAGE.md` documents the response shape but not the error messages, per-endpoint
status codes, or what counts as a breaking change. Consumers have to read the source.

Fix: add an error list and a versioning note.

### 14. No request id or tenant in logs

`core/middleware.py:20-22` logs only method, path, status, and latency.

Fix: accept `X-Request-ID` (generate if missing) and add it plus the tenant to log lines.

---

## Minor

### 15. Docs list only two LLM validators

`API_USAGE.md:9, 349, 354-356, 398`, `docs/llm_prompt_configs/create_config.md`, and
`docs/llm_prompt_configs/list_configs.md` list only `topic_relevance` and
`answer_relevance_custom_llm`. Add `topic_relevance_llm` (plain-text scope prompt, same
as `topic_relevance`, no placeholder rules).

### 16. `validator_configs.list` has no pagination

`routes/validator_configs.py:45-57` has filters but no offset/limit, unlike the ban-list
and prompt-config lists.

### 17. `health_check` returns a raw bool

`routes/utils.py:11` returns `True`, breaking the "all endpoints return `APIResponse`"
statement in `API_USAGE.md:35-46`. Wrap it or document the exception.

### 18. `type=` shadows the builtin

`routes/validator_configs.py:52`: rename the query param to `validator_type`.

### 19. Duplicate error extraction

`routes/guardrails.py:267-271` and `277-280` both call `_extract_error_from_guard`.
Consolidate inside `_finalize`.

### 20. `suppress_pass_logs` has two different defaults

Route defaults `True` (`guardrails.py:53`), helper defaults `False` (`guardrails.py:187`).
Make them agree.

### 21. Docstring says it returns a value but returns None

`routes/guardrails.py:113-122`: `_resolve_validator_configs` returns `None`.

### 22. `_redact_input` is fragile

`routes/guardrails.py:314-316` splits on `":\n\n"` then does a plain `str.replace`. Works
today, breaks if the input contains those characters structurally.

### 23. POSTs return 200 not 201

All POST routes. Cosmetic.

### 24. `response_model_exclude_none` set on one route only

`routes/guardrails.py:47`. Standardize across endpoints.

### 25. Delete does get-then-delete

`routes/llm_prompt_configs.py:109-121`: two round-trips. Only matters if hot.

### 26. `response_id` is a server UUID, not a provider id

`routes/guardrails.py:196`. If a provider response id is added later, keep them as
separate columns.

### 27. Commented-out import

`api/main.py:18-19`: delete the commented `private.router` import.

### 28. Document that the auth token must be random

`_hash_token` (`deps.py:29-30`) is unsalted SHA-256 — fine only because `AUTH_TOKEN` is a
high-entropy secret. Note that requirement so no one sets a memorable string.

### 29. 404 masks "wrong tenant" vs "missing"

`crud/validator_config.py:79-95` (and `crud/llm_prompt_config.py:44-59`) return the same
404 for both. Correct for isolation — add a comment so a refactor doesn't split them.
