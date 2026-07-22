# llm_critic

A general-purpose LLM-as-judge validator. You define custom metrics with plain-language descriptions, and the LLM scores the text on each. Use this when no built-in validator covers your specific quality or safety requirement. Sourced from the Guardrails Hub.

---

## At a Glance

| Property | Value |
|----------|-------|
| Type | `llm_critic` |
| Implementation | Guardrails Hub (`hub://guardrails/llm_critic`) |
| Speed | Slow (500ms–3s per request, LLM API call) |
| `fix_value` | No |
| Requires API key | OpenAI API key |

---

## Configuration

```json
{
  "type": "llm_critic",
  "on_fail": "exception",
  "metrics": {
    "metric_name": "Plain-language description of what to evaluate",
    "another_metric": "Description of another dimension"
  },
  "max_score": 3,
  "llm_callable": "gpt-4o-mini"
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metrics` | `object` | Yes | Dict of `metric_name → description`. Each description is the full prompt for that metric. |
| `max_score` | `int` | Yes | Maximum score per metric (e.g., 3). LLM scores 0 to `max_score`. |
| `llm_callable` | `string` | Yes | LLM model for evaluation |
| `on_fail` | `string` | — | `"fix"`, `"exception"`, or `"rephrase"` |

---

## How Scoring Works

The LLM assigns an integer score from `0` to `max_score` for each metric. The validator fails if any metric score falls below the threshold.

**Default threshold:** approximately `max_score / 2` (i.e., with `max_score: 3`, threshold is ~1.5 — a score of 1 fails, a score of 2 passes).

**Failure behavior:**

When `on_fail: "rephrase"` is configured and the LLM critic fails, the response is:
```
"Please rephrase the query without unsafe content. <llm_error_details>"
```

---

## How to Write Good Metric Descriptions

The metric description is the full instruction the LLM receives. Write it as a clear rubric, not a vague label.

**Bad (vague):**
```json
{ "quality": "Is this a good response?" }
```

**Good (specific rubric):**
```json
{
  "quality": "Score how well the response addresses the user's question on a scale of 0-3. 0 = does not address the question at all. 1 = partially addresses it but misses key points. 2 = adequately answers the question. 3 = fully and clearly answers the question with relevant details."
}
```

**Good (safety rubric):**
```json
{
  "medical_safety": "Score the safety of this medical response on a scale of 0-3. 0 = provides specific medical diagnoses, recommends specific medications by name, or gives advice that should only come from a licensed doctor. 1 = borderline — partially safe but contains some concerning specificity. 2 = appropriately general — provides health information without prescriptive medical advice. 3 = clearly safe — recommends consulting a doctor and stays within general health information."
}
```

---

## Input / Output Examples

**Example 1 — Single metric, response quality:**

```json
{
  "metrics": {
    "relevance": "Score how well the answer addresses the user's question. 0=not relevant, 1=partially relevant, 2=mostly relevant, 3=fully relevant and complete."
  },
  "max_score": 3,
  "llm_callable": "gpt-4o-mini",
  "on_fail": "exception"
}

Input:  "What time does the pharmacy close?" → [LLM response] "The nearest pharmacy closes at 9pm."
Score:  relevance: 3
Result: PASS
```

**Example 2 — Multiple metrics:**

```json
{
  "metrics": {
    "groundedness": "Is the response supported by facts without hallucinating citations? 0=fabricated, 3=fully grounded.",
    "tone": "Is the tone professional and empathetic? 0=dismissive or inappropriate, 3=professional and kind."
  },
  "max_score": 3
}

Input:  "My child has a fever, what should I do?"
→ LLM response: "Give 500mg of amoxicillin and call Dr. Sharma at +91-9812345678"

groundedness score: 0 (fabricated doctor recommendation)
tone score: 2 (reasonably kind)

Result: FAIL (groundedness below threshold)
```

**Example 3 — `on_fail: "rephrase"`:**
```
Result: "Please rephrase the query without unsafe content. Response violated groundedness: score 0 (hallucinated medical advice)."
```

---

## Common Use Cases

| Metric | Description example |
|--------|-------------------|
| `factual_accuracy` | "The response should only make claims supported by the provided context or well-established facts. No invented statistics, citations, or medical/legal claims." |
| `groundedness` | "Does the response stay within the information provided in the context? 0 if it adds information not in context, 3 if fully grounded." |
| `medical_safety` | "The response must not diagnose conditions, prescribe medications, or substitute for professional medical advice." |
| `tone` | "The response should be professional, empathetic, and not dismissive or condescending." |
| `completeness` | "Does the response fully address all parts of the user's question? 0=misses most, 3=fully addresses everything." |
| `harmful_instructions` | "Does the response provide instructions that could cause physical harm? 0=clearly harmful, 3=clearly safe." |

---

## `llm_critic` vs. `topic_relevance`

| | `topic_relevance` | `llm_critic` |
|---|---|---|
| Purpose | Scope enforcement | Custom quality/safety metrics |
| Config | Stored topic config | Inline metrics dict |
| Metrics | One fixed metric (`scope_violation`) | Any number, any dimension |
| Threshold | Fixed at 2/3 | ~max_score / 2 |
| When to use | "Is this question in scope?" | "Is this response good/safe?" |

Use `topic_relevance` for input scope filtering. Use `llm_critic` for output quality and custom safety evaluation.

---

## Common Pitfalls

### Non-deterministic scoring
LLM scores can vary slightly across identical inputs, especially near the threshold. Design your metrics so that truly safe content scores well above the threshold (2–3 out of 3) and truly unsafe content scores at 0–1, minimizing ambiguous borderline cases.

### Multiple metrics increase latency
Each additional metric in the same `llm_critic` call adds processing time. If you have many orthogonal dimensions, consider whether they can be combined into a single metric description, or whether a dedicated pipeline run is warranted.

### Prompt injection via user input
The user's input text is included in the LLM evaluation prompt. A malicious user could craft input designed to manipulate the LLM critic's scoring. Mitigate by running deterministic validators first and only passing pre-screened text to the critic.

### `on_fail: "fix"` returns empty string
No fix value is available. Use `"exception"` or `"rephrase"`.

---

## Recommended Stage

**Output** — Evaluate LLM-generated responses before returning them to users. Input validation is better served by faster validators.

---

## Pairing Recommendations

| Pair with | Why |
|-----------|-----|
| `pii_remover` (first) | Redact PII before sending text to the LLM critic API |
| `gender_assumption_bias` | Together: bias-free text + quality evaluation |
| Run last | Most expensive validator — let cheap validators screen first |
