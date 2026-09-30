# `topic_relevance` vs `topic_relevance_llm` — Comparative Study

Both validators answer the same question: *is this user message within the configured
topic scope?* They differ in how they ask an LLM. This document compares them on
implementation, measured accuracy, latency, and failure behaviour, and recommends
which one to keep.

- **Date of measurement:** 2026-09-30
- **Model:** `gpt-4o-mini` (`settings.DEFAULT_LLM_CALLABLE`)
- **Datasets:** education (192 rows, 125 in-scope / 67 out), healthcare (163 rows, 115 / 48)
- **Total live calls:** 2,840

---

## At a Glance

| Property | `topic_relevance` | `topic_relevance_llm` |
|---|---|---|
| Source | [`topic_relevance.py`](../../backend/app/core/validators/topic_relevance.py) | [`topic_relevance_llm.py`](../../backend/app/core/validators/topic_relevance_llm.py) |
| Engine | Guardrails Hub `LLMCritic` (vendored, 0.10.0) | Direct `litellm.completion` |
| Prompt delivery | Template `json.dumps`'d into LLMCritic's own wrapper, user text interpolated into the same `user` message | Scope prompt + rules as `system`, user text as a separate `user` message |
| Threshold | Hardcoded `2`, `max_score=3` | Configurable `1–3` (default `TOPIC_RELEVANCE_LLM_THRESHOLD` = 2) |
| Returns `scope_score` | **No — always `null`** | Yes |
| Extra metadata | None | `interpreted_meaning`, `reasoning`, `classification_confidence_score` |
| JSON mode | Requested but **silently dropped** | Applied |
| `max_tokens` | Uncapped | 300 |
| Unit tests | **None** | 31 |
| Mean latency | ~920 ms | ~1,400 ms |

---

## Headline Result

On the prompt version that actually matches the shipped topic configs (v3), the two
validators are close, with the LLM variant ahead on every metric in education and on
precision in healthcare:

| Domain | Backend | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|---|
| education | `topic_relevance` | 0.92 | 0.93 | 0.82 | 0.87 |
| education | `topic_relevance_llm` | **0.94** | **0.95** | **0.87** | **0.91** |
| healthcare | `topic_relevance` | 0.87 | 0.82 | **0.69** | 0.75 |
| healthcare | `topic_relevance_llm` | **0.91** | **1.00** | **0.69** | **0.81** |

The decisive difference is not accuracy — it is that `topic_relevance` cannot tell you
*why* it made a decision, and `topic_relevance_llm` can.

---

## The Prompt-Version Mismatch

**This is the largest single effect measured, and it affects both validators equally.**

Both shipped topic configs are written purely as *forbidden-topic* definitions:

> This assistant supports students with education-related topics. It does not answer
> questions in the following forbidden topics: Homework solving: … Illegal topics: …

That framing matches prompt schema **v2** (forbidden-only) and **v3** (combined). But
[`run.py`](../../backend/app/evaluation/topic_relevance/run.py) pins
`prompt_schema_version=1`, and v1 is allow-list framing:

> If the query relates to ANY listed topic area, score 2 or higher.
> Only score 1 if the query is COMPLETELY unrelated to all topics.

Under v1 the *listed topics are the forbidden ones*, so the prompt instructs the model to
**pass** exactly the messages it should block. Measured effect:

| Domain | Backend | v1 F1 | v2 F1 | v3 F1 |
|---|---|---|---|---|
| education | `topic_relevance` | 0.25 | 0.79 | **0.87** |
| education | `topic_relevance_llm` | 0.26 | 0.90 | **0.91** |
| healthcare | `topic_relevance` | 0.25 | 0.74 | **0.75** |
| healthcare | `topic_relevance_llm` | 0.32 | 0.82 | **0.81** |

Recall on v1 is 0.15–0.19. On v3 it is 0.69–0.87. Concretely, under v1 the query
*"how to become a lawyer in India?"* — labelled `OUT_OF_SCOPE` — passes both validators.

**Consequence:** any accuracy figure previously produced by the committed harness is
invalid, for both validators. Fix the harness default before quoting numbers from it.

---

## Confirmed Defects

### `topic_relevance`

**1. `scope_score` is always `null`.** Confirmed on 355/355 rows, both domains.
[`topic_relevance.py:109-112`](../../backend/app/core/validators/topic_relevance.py#L109-L112)
reads `result.metadata.get("scope_violation")`, but `LLMCritic.validate` returns a bare
`PassResult()` / `FailResult(error_message=...)` and never populates `metadata`. The score
exists — LLMCritic prints it to stdout — but is discarded before the validator sees it.
The `scope_score` column in `outputs/topic_relevance/*-predictions.csv` is entirely empty,
so per-score threshold analysis is impossible for this backend.

**2. JSON mode is silently dropped.**
[`topic_relevance.py:92-96`](../../backend/app/core/validators/topic_relevance.py#L92-L96)
passes `llm_kwargs={"response_format": ...}`. `LLMCritic.__init__` forwards `**kwargs` only
to `Validator.__init__`; its `get_llm_response` calls
`completion(model=..., messages=..., **kwargs)` where `kwargs` contains just `api_key`.
The parameter never reaches the API.

**3. `print()` on every call.** `LLMCritic.validate` writes its parsed evaluation to stdout
per validation — unstructured noise in production logs and in the eval harness.

**4. No unit tests.** `topic_relevance_llm` has 31 across two files; `topic_relevance` has none.

### `topic_relevance_llm`

**5. `prompt_schema_version` is dropped at the route.**
[`guardrails.py:211-213`](../../backend/app/api/routes/guardrails.py#L211-L213) copies
`config.prompt_schema_version` onto `TopicRelevanceSafetyValidatorConfig` only. A version
stored on a `topic_relevance_llm` config is ignored, so it silently runs v1 — the worst
version, per the table above.

**6. Not registered as an LLM validator.**
[`core/enum.py:4-6`](../../backend/app/core/enum.py#L4-L6) has no `TopicRelevanceLLM` member,
and [`guardrails.py:204`](../../backend/app/api/routes/guardrails.py#L204) requires
`config.validator_name == TopicRelevance` for *both* validators. A `topic_relevance_llm`
validator must borrow a `topic_relevance` config, and nothing stops the reverse.

Defects 5 and 6 are items 8, 3 and 4 in
[`tech-readiness-topic-relevance-llm.md`](../tech-readiness-topic-relevance-llm.md) and are
still present.

### Documentation

**7.** [`topic-relevance.md`](./topic-relevance.md) documents score `0` as "completely
off-topic", a valid scoring band. It is not: the prompts emit 1–3 only, and LLMCritic
classifies `0` as an *invalid* evaluation. There is also no `topic-relevance-llm.md`.

---

## Latent Risks (not observed in this run)

Stated as risks because **zero** occurred across all 2,840 calls — neither validator
produced a single parse failure or non-scope error. They remain structural, not measured.

- **`topic_relevance` conflates model failure with scope rejection.** LLMCritic's wrapper
  prompt says "score between 0 and Max score" while our injected description says 1–3. A
  returned `0` lands in `missing_invalid_metrics` → `FailResult("missing or has invalid
  evaluations")`, which
  [`topic_relevance.py:117-121`](../../backend/app/core/validators/topic_relevance.py#L117-L121)
  rewrites to `TOPIC_OUT_OF_SCOPE_ERROR`. A malformed response would reach the user as a
  scope rejection. The LLM variant reports parse failures distinctly, with the raw text.
- **`topic_relevance` is more exposed to prompt injection.** LLMCritic places instructions
  and user text in a single `user` message, with the text interpolated *before* the metric
  definitions. The LLM variant isolates user text in its own turn.
- **`topic_relevance_llm` has a tight token budget.** Four fields including free-text
  reasoning within `max_tokens=300`; a verbose response could truncate mid-JSON.
  `_extract_first_json_object` tolerates surrounding prose but not truncation.
- **`topic_relevance` has no token cap at all**, so a pathological response is unbounded.

---

## Latency

| Backend | Mean | p95 | Max |
|---|---|---|---|
| `topic_relevance` | 921 / 949 ms | 1,239 / 1,462 ms | 3,080 / 2,790 ms |
| `topic_relevance_llm` | 1,445 / 1,353 ms | 1,938 / 1,748 ms | 9,062 / 2,553 ms |

(education / healthcare, sequential, from the canonical harness.)

`topic_relevance` is ~1.4–1.5× faster **despite sending roughly double the prompt tokens**
— LLMCritic wraps the template in `json.dumps(metrics, indent=4)` plus its own preamble.
Output length dominates: the Critic emits a single integer, the LLM variant emits four
fields including two sentences of prose. The ~450 ms gap is the price of the metadata.

Tail latency is the one place `topic_relevance_llm` is clearly worse: a 9.06 s worst case
in education against 3.08 s for the Critic, again because a long prose response takes
longer to generate. If a per-request deadline matters, set it against the p95 (~1.9 s) and
treat the tail as a timeout case rather than assuming the mean.

---

## Per-Category Findings (v3)

Recall by ground-truth category, out-of-scope rows only:

| Domain | Category | n | `topic_relevance` | `topic_relevance_llm` |
|---|---|---|---|---|
| education | Misc | 51 | 0.84 | 0.88 |
| education | Homework solving | 6 | 0.83 | 0.67 |
| education | Non-STEM fields | 3 | **0.00** | 1.00 |
| education | Personal issues | 4 | 1.00 | 0.75 |
| education | Illegal topics / PII | 3 | 1.00 | 1.00 |
| healthcare | **Nutrition** | 20 | **0.00** | **0.00** |
| healthcare | Beauty/Weight | 13 | 0.46 | 0.54 |
| healthcare | Non-Reproductive health | 7 | 0.71 | 0.71 |
| healthcare | Misc | 10 | 0.60 | 0.50 |
| healthcare | Sex determination | 16 | 1.00 | 1.00 |

**`Nutrition` is a shared blind spot: 0.00 recall on 20 samples for both backends.** This
is not a validator difference — it is a prompt/config problem. The healthcare config
forbids "general dietary or food nutrition advice unrelated to pregnancy or infant care"
while the assistant's stated purpose is maternal and family health, so the model reads
nutrition questions as in-scope. Healthcare recall cannot exceed ~0.69 until this category
is disambiguated. `Beauty/Weight` (0.46–0.54) is the second weakest and carries similar
carve-out language.

Sex determination — the highest-stakes category for this deployment — is caught perfectly
by both.

---

## Dataset Issue

`healthcare-topic-relevance-dataset.csv` contains both `Sex Determination` and
`Sex determination` as category values. `groupby("category")` treats them as two groups,
splitting a 16-sample category into 10 and 6 and distorting per-category tables. Normalise
the casing in the source CSV.

---

## Reproducing

Datasets are gitignored; download the four files into
`backend/app/evaluation/datasets/topic_relevance/` per
[the evaluation README](../../backend/app/evaluation/README.md). Requires `OPENAI_API_KEY`.

```bash
cd backend
set -a && . ../.env && set +a
.venv/bin/python app/evaluation/topic_relevance/run.py
```

Writes `outputs/topic_relevance/` and `outputs/topic_relevance_llm/` (v1 only — see the
mismatch section above).

The prompt-version sweep behind the v1/v2/v3 tables is a separate script. It runs both
backends × both domains × v1/v2/v3 with an 8-way thread pool and writes
`outputs/topic_relevance_comparison/matrix.json` plus per-cell prediction CSVs:

```bash
.venv/bin/python app/evaluation/topic_relevance/sweep.py
```

Latency recorded there is wall-clock under concurrency and is **not** comparable to the
sequential harness figures; the latency table above uses the harness numbers only.

---

## Recommendation

**Keep `topic_relevance_llm`; deprecate `topic_relevance`.**

It wins or ties on accuracy at every prompt version and in both domains, and it is the
only one of the two that returns a usable score, explains its decision, distinguishes
model failure from scope rejection, honours JSON mode, caps its token spend, isolates user
text from instructions, and has tests. Its sole measured cost is ~450 ms of latency.

`topic_relevance`'s defects live in vendored third-party code — fixing the null
`scope_score` or the dropped `response_format` means forking `guardrails_ai.llm_critic`.
That is not worth doing for a validator that is already behind on accuracy.

Ordered next steps:

1. **Fix the harness default.** `prompt_schema_version=3` in `run.py`, or make it a sweep
   parameter. Until then the committed harness reports F1 ≈ 0.25 for both validators and
   any number quoted from it is wrong.
2. **Unblock `topic_relevance_llm`** — add `TopicRelevanceLLM` to `LLMValidatorName` and
   bind each validator to its own config name (defects 5 and 6).
3. **Disambiguate the `Nutrition` carve-out** in the healthcare config. It is worth more
   recall than any validator choice.
4. **Normalise the `Sex determination` casing** in the healthcare dataset.
5. **Write `docs/validators/topic-relevance-llm.md`** and correct the score-`0` claim in
   `topic-relevance.md`.
6. **Deprecate `topic_relevance`** once consumers are migrated.
