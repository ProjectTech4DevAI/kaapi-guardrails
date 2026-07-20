# topic_relevance

Validates whether a user message falls within the configured topic scope, using an LLM-as-judge. Define what "on-topic" means in plain language — no training required. Designed to prevent users from repurposing your assistant for unrelated tasks.

---

## At a Glance

| Property | Value |
|----------|-------|
| Type | `topic_relevance` |
| Implementation | Local (wraps Guardrails Hub `LLMCritic`) |
| Speed | Slow (500ms–2s, LLM API call) |
| `fix_value` | No |
| Requires API key | OpenAI API key |

---

## Configuration

```json
{
  "type": "topic_relevance",
  "on_fail": "rephrase",
  "topic_relevance_config_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "llm_callable": "gpt-4o-mini"
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `topic_relevance_config_id` | `UUID` | required | ID of a stored topic relevance config |
| `llm_callable` | `string` | `"gpt-4o-mini"` | LLM model for evaluation |
| `prompt_schema_version` | `int` | `1` | Prompt template version to use |
| `on_fail` | `string` | `"fix"` | `"fix"`, `"exception"`, or `"rephrase"` |

---

## Setting Up a Topic Config

Topic relevance requires a stored configuration that defines the scope of your assistant in plain language.

**Create a topic config:**

```bash
POST /api/v1/guardrails/topic_relevance_configs/
Authorization: X-API-KEY your-api-key

{
  "name": "Healthcare Assistant Scope",
  "configuration": "This assistant helps users with questions about symptoms, medications, preventive care, and general health information. It should NOT answer questions about cooking, sports, politics, technology, financial advice, or any topic unrelated to health and medicine."
}
```

**Update a topic config:**

```bash
PATCH /api/v1/guardrails/topic_relevance_configs/{id}

{
  "configuration": "Updated scope description..."
}
```

**List topic configs:**

```bash
GET /api/v1/guardrails/topic_relevance_configs/?organization_id=1&project_id=101
```

---

## How It Works Internally

1. **Config resolution** — The API fetches the topic configuration string from the database using `topic_relevance_config_id`.

2. **Prompt building** — The topic configuration is injected into a versioned prompt template (stored in `backend/app/core/validators/prompts/topic_relevance/v1.md`). The resulting prompt instructs the LLM to score the input text on a `scope_violation` metric.

3. **LLMCritic scoring** — The `TopicRelevance` validator delegates to Guardrails Hub's `LLMCritic` with a single metric: `scope_violation`. The metric description contains the full prompt including the topic configuration. The max score is 3, and the threshold is 2.

4. **Score interpretation:**
   - Score ≥ 2: Input is within scope → `PassResult` (with `metadata.scope_score`)
   - Score < 2: Input is outside scope → `FailResult` (with `metadata.scope_score`)

5. **JSON mode** — If the configured LLM supports `response_format: json_object` (detected via LiteLLM), the validator uses it for more reliable structured output.

---

## Scoring

| Score | Meaning |
|-------|---------|
| 0 | Completely off-topic |
| 1 | Marginally related but not within scope |
| 2 | Partially within scope — passes |
| 3 | Clearly within scope — passes |

The threshold is fixed at 2. There is no configuration to change it.

---

## Writing Effective Topic Configs

The quality of your topic config directly determines detection accuracy.

**Too narrow (causes false positives):**
```
"This assistant answers questions about diabetes."
```
Users asking about blood sugar monitoring, insulin, or diet for diabetics might get rejected.

**Too broad (defeats the purpose):**
```
"This assistant answers health questions."
```
Almost any question can be framed as health-adjacent.

**Well-calibrated:**
```
"This assistant supports users of the Kaapi health platform with questions about 
managing chronic conditions, understanding lab reports, medication reminders, 
and preventive care. It may also help with general wellness questions.

Out of scope: cooking recipes (unless directly related to a medical diet), 
financial advice, legal matters, technology support, entertainment, 
sports, and any topic unrelated to health management."
```

**Tips:**
- Explicitly list out-of-scope topics — the LLM scores more accurately with positive and negative examples
- Include 2–3 examples of in-scope questions in the config
- Test against 20+ representative inputs before deploying
- Review the `scope_score` in validator logs for borderline cases

---

## Input / Output Examples

**Example 1 — Clearly in scope:**
```
Topic config: "Healthcare assistant for symptoms and medication questions"

Input:  "What are the side effects of metformin?"
Score:  3
Result: PASS
```

**Example 2 — Clearly out of scope:**
```
Input:  "Who won the cricket World Cup in 2023?"
Score:  0
Result: FAIL
Output: "Please rephrase the query..." (on_fail: rephrase)
```

**Example 3 — Borderline:**
```
Input:  "What foods should I eat to lose weight?"
Score:  1 or 2 (depends on how the config is written)
Result: May PASS or FAIL — test and tune your config
```

**Example 4 — Off-topic with health framing:**
```
Input:  "Is it healthy to watch cricket?" 
Score:  1 (mentions health but primarily about sport)
Result: Likely FAIL with a well-written config
```

---

## Common Pitfalls

### LLM non-determinism
The LLM score for the same input can vary slightly across calls. Borderline inputs (score ≈ 1–2) may flip between pass and fail. This is expected behavior — use a well-calibrated config to minimize borderline cases.

### LLM hallucination in scoring
The LLM is making a judgment call. Test your config carefully against edge cases before production deployment.

### Latency
Every validation triggers an LLM API call (500ms–2s). Put this last in your pipeline after fast validators have already blocked obvious violations.

### `on_fail: "fix"` returns empty string
No fix value is available. Use `"rephrase"` (prompts user to rewrite) or `"exception"` (hard block).

---

## Recommended Stage

**Input** — Enforce domain scope on user messages before the LLM processes them. No point running the LLM if the query is out of scope.

---

## Pairing Recommendations

| Pair with | Why |
|-----------|-----|
| `ban_list` | Ban list handles specific prohibited terms; topic relevance handles off-domain queries semantically |
| `pii_remover` first | Always redact PII before sending the topic config + user text to an LLM API |
| Run last in chain | Topic relevance is slow — let fast validators block obvious violations first |
