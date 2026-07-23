# answer_relevance_custom_llm

Validates whether an LLM-generated answer is actually relevant to the user's query. Uses an LLM-as-judge with a configurable prompt template. Detects non-answers, deflections, and hallucinated responses that technically respond but don't address the question.

---

## At a Glance

| Property | Value |
|----------|-------|
| Type | `answer_relevance_custom_llm` |
| Implementation | Local (LiteLLM-based) |
| Speed | Slow (500ms–2s, LLM API call) |
| `fix_value` | No |
| Requires API key | OpenAI API key |

---

## Configuration

```json
{
  "type": "answer_relevance_custom_llm",
  "on_fail": "exception",
  "llm_callable": "gpt-4o-mini",
  "custom_prompt_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `llm_callable` | `string` | `"gpt-4o-mini"` | LLM model for evaluation |
| `prompt_template` | `string` | Default template | Inline prompt template with `{query}` and `{answer}` placeholders |
| `custom_prompt_id` | `UUID` | — | ID of a stored custom prompt. Resolved to `prompt_template` before validation. |
| `on_fail` | `string` | `"fix"` | `"fix"`, `"exception"`, or `"rephrase"` |

> Provide at most one of `prompt_template` or `custom_prompt_id`. If neither is provided, the built-in default prompt is used.

---

## Critical: Input Format

Unlike other validators that receive raw text, `answer_relevance_custom_llm` expects the `input` field to be a **JSON string** with both the query and the answer:

```json
{
  "input": "{\"query\": \"What is the capital of France?\", \"answer\": \"Paris is the capital of France.\"}"
}
```

This is because the validator needs both the original question and the LLM's response to assess relevance. Your application is responsible for formatting the input this way.

**Validator behavior on malformed input:**

```
Input:  "just some plain text"
Result: FAIL — "Input must be a JSON string with 'query' and 'answer' fields."
```

---

## Default Prompt Template

```
Query: {query}
Answer: {answer}

Does the answer fully satisfy the query and constraints?
Answer only YES or NO.
```

The validator sends this prompt to the LLM and parses the response:
- Response starts with `YES` → `PassResult`
- Response starts with `NO` → `FailResult` with `error_message: "The answer is not relevant to the query."`
- Any other response → `FailResult` with the unexpected response logged

---

## Custom Prompt Templates

The default prompt works well for general use, but you may want domain-specific evaluation criteria. Use custom prompts to add context or constraints.

**Managing stored prompts:**

```bash
# Create a custom prompt
POST /api/v1/guardrails/answer_relevance_prompts/
Authorization: Bearer <token>
X-ORGANIZATION-ID: 1
X-PROJECT-ID: 101

{
  "name": "Healthcare Relevance Check",
  "description": "Evaluates if a health-related answer fully addresses the user's question",
  "prompt_template": "Query: {query}\nAnswer: {answer}\n\nDoes the answer:\n1. Directly address the health question?\n2. Recommend consulting a doctor when appropriate?\n3. Avoid providing specific diagnoses?\nAnswer YES only if all applicable criteria are met. Otherwise answer NO."
}
```

```bash
# Update a prompt
PATCH /api/v1/guardrails/answer_relevance_prompts/{id}

# List prompts
GET /api/v1/guardrails/answer_relevance_prompts/?organization_id=1&project_id=101

# Delete a prompt
DELETE /api/v1/guardrails/answer_relevance_prompts/{id}
```

**Use the stored prompt in a request:**
```json
{
  "type": "answer_relevance_custom_llm",
  "on_fail": "exception",
  "custom_prompt_id": "your-prompt-uuid"
}
```

---

## How It Works Internally

1. **Input parsing** — The validator expects the `value` to be a JSON string. It parses `query` and `answer` from it. Returns a `FailResult` immediately if the JSON is malformed or either field is empty.

2. **Prompt construction** — The `prompt_template` is formatted with `{query}` and `{answer}` substituted. Returns a `FailResult` if a required placeholder is missing from the template.

3. **LLM call** — Sends the constructed prompt to the configured LLM via LiteLLM. Sets `max_tokens=10` since only a YES/NO response is needed.

4. **Response parsing** — The LLM response is stripped and uppercased. The validator looks for a `YES` or `NO` prefix. Unexpected responses are treated as failures.

5. **Error handling** — LLM API exceptions are caught and returned as `FailResult` with the exception message.

---

## Input / Output Examples

**Example 1 — Relevant answer:**
```json
{
  "input": "{\"query\": \"How do I reset my password?\", \"answer\": \"To reset your password, click on 'Forgot Password' on the login page, enter your email, and follow the link sent to your inbox.\"}"
}

LLM prompt: "...Does the answer fully satisfy the query? Answer only YES or NO."
LLM response: "YES"
Result: PASS
```

**Example 2 — Irrelevant answer:**
```json
{
  "input": "{\"query\": \"What are the side effects of ibuprofen?\", \"answer\": \"Ibuprofen is a common medication used for pain relief.\"}"
}

LLM response: "NO" (answer doesn't address side effects)
Result: FAIL — "The answer is not relevant to the query."
Output: safe_text: null (on_fail: exception)
```

**Example 3 — Answer addresses a different question:**
```json
{
  "input": "{\"query\": \"What documents do I need for the loan application?\", \"answer\": \"We offer various loan products with competitive interest rates.\"}"
}

LLM response: "NO" (answer is a sales pitch, not an answer to the documents question)
Result: FAIL
```

**Example 4 — Malformed input:**
```json
{
  "input": "What is the capital of France?"
}

Result: FAIL — "Input must be a JSON string with 'query' and 'answer' fields."
```

---

## When to Use This Validator

`answer_relevance_custom_llm` is specifically for **output validation** — checking that the LLM's response actually answered the question.

**Use it when:**
- Your LLM sometimes deflects, goes off-topic, or gives generic non-answers
- You need to ensure responses address the specific question asked
- You're building a RAG system and want to verify answers stay grounded to the query
- You have domain-specific relevance criteria (e.g., healthcare responses must include safety disclaimers)

**Don't use it for:**
- Input validation — it requires both a query AND an answer
- Catching toxic or unsafe content — use `uli_slur_match`, `llamaguard_7b`, etc.
- Checking factual accuracy — use `llm_critic` with a `groundedness` metric

---

## `answer_relevance_custom_llm` vs. `llm_critic`

| | `answer_relevance_custom_llm` | `llm_critic` |
|---|---|---|
| Input format | JSON with `{query, answer}` | Plain text |
| Evaluation | Binary YES/NO relevance | Scored 0–max_score per metric |
| Custom criteria | Via prompt template | Via metric descriptions |
| Use case | "Did the LLM answer the question?" | "How good/safe is the response?" |

Use `answer_relevance` for the fundamental yes/no question of whether the response addressed the query. Use `llm_critic` for nuanced multi-dimensional quality evaluation.

---

## Common Pitfalls

### Input must be JSON
This is the biggest gotcha. Your application code must serialize the query+answer pair as a JSON string before sending to the guardrails API. Plain text input always fails.

```python
import json
guardrail_input = json.dumps({"query": user_query, "answer": llm_response})
```

### Prompt template must contain `{query}` and `{answer}`
If your custom prompt template is missing either placeholder, the validator fails with a clear error. Always test custom templates before deploying.

### Non-deterministic YES/NO
The LLM sometimes responds with "YES, the answer..." or "NO, because...". The validator handles this by checking `.startswith("YES")` and `.startswith("NO")`, so longer responses work. Truly unexpected responses (e.g., "MAYBE") are treated as failures.

### `on_fail: "fix"` returns empty string
No fix is available. Use `"exception"` or `"rephrase"`.

---

## Recommended Stage

**Output only** — This validator requires both the query and the answer, so it can only run after the LLM has generated a response.

---

## Pairing Recommendations

| Pair with | Why |
|-----------|-----|
| `pii_remover` (before) | Redact PII from the LLM response before sending it to this validator's LLM call |
| `llm_critic` | For comprehensive output validation: relevance + quality + safety together |
| `gender_assumption_bias` (before) | Fix bias in the text before the relevance check |
