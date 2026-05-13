# Core Concepts

Understanding the mental model behind Kaapi Guardrails.

---

## Validators

A **validator** is a function that takes text as input and returns either:

- **Pass** — text is safe, return it as-is (or with minor fixes)
- **Fail** — text violates a rule; apply the configured `on_fail` action

Each validator has a single responsibility. `pii_remover` does not check for toxicity. `uli_slur_match` does not redact phone numbers. Compose them together to build layered safety.

---

## The Validation Pipeline

Validators run **sequentially**, in the order you specify. The output of one validator becomes the input to the next.

```
Input Text
    │
    ▼
┌─────────────────┐
│  pii_remover    │  → fixes PII, passes redacted text forward
└────────┬────────┘
         │
    ▼
┌─────────────────┐
│ uli_slur_match  │  → checks redacted text for slurs, fixes if found
└────────┬────────┘
         │
    ▼
┌─────────────────┐
│  nsfw_text      │  → checks for NSFW content
└────────┬────────┘
         │
    ▼
 Safe Text (or null if exception fired)
```

**Order matters.** Run cheap, fast validators first. Run LLM-based validators last.

---

## On-Fail Actions

When a validator detects a violation, the `on_fail` setting controls what happens next.

| Action | Behavior | Use when |
|--------|----------|----------|
| `fix` (default) | Returns the corrected text (redacted, neutralized). If no fix is possible, returns empty string | You want the pipeline to continue with a cleaned version |
| `exception` | Halts the pipeline, returns `safe_text: null` and an error | You want a hard block — no output if the content is unsafe |
| `rephrase` | Returns a fixed message asking the user to rephrase | You want to signal the user to rewrite their input (e.g., for chatbots) |

**`rephrase` response example:**

```json
{
  "rephrase_needed": true,
  "safe_text": "Please rephrase the query without unsafe content..."
}
```

Your application should check `rephrase_needed: true` and prompt the user accordingly.

---

## Input vs. Output Validation

You can validate at two points in the LLM flow.

**Input validation** (before the LLM):
- Catches jailbreaks, abusive prompts, off-topic requests and PII in user queries
- Cheaper: stops bad prompts before spending LLM tokens
- Validators: `uli_slur_match`, `ban_list`, `topic_relevance`, `llamaguard_7b`, `pii_remover`

**Output validation** (after the LLM):
- Catches model hallucinations, biased language, toxic content
- Validates what users actually see
- Validators: `gender_assumption_bias`, `nsfw_text`, `llm_critic`

Use the `stage` field when creating stored validator configs (`"stage": "input"` or `"stage": "output"`).

---

## Deterministic vs. LLM-Based Validators

A critical design decision is choosing the right type of validator for your use case.

| Type | Speed | Cost | Explainable | Nuanced | Examples |
|------|-------|------|------------|---------|---------|
| Lexical / regex | Fast | Free | Yes | No | `uli_slur_match`, `ban_list`, `profanity_free` |
| Embeddings / ML model | Fast | Low | Partial | Partial | `nsfw_text`, `llamaguard_7b` |
| LLM critic | Slow | Medium | Yes | Yes | `topic_relevance`, `llm_critic` |

**Rule of thumb:** Start with deterministic validators. Add LLM-based validators only for cases where context and nuance matter — and always put them last in the chain.

---

## Confidence Scores

Some validators return a confidence score alongside pass/fail:

- **`pii_remover`** — Presidio assigns a confidence score (0–1) per detected entity. The `threshold` config sets the minimum confidence required to redact.
- **`nsfw_text`** — HuggingFace transformer returns a probability score. The `threshold` config sets the cutoff.
- **`topic_relevance`** — LLM critic scores relevance 0–3. The pipeline fails if score < 2.
- **`llm_critic`** — Per-metric scores (0–`max_score`). Configurable threshold per metric.

Validators without scores (e.g., `uli_slur_match`, `ban_list`) are binary: match found or not.

---

## Stored Validator Configs

Rather than sending full validator configs in every request, you can store them in the database and reference them by ID. This is useful for:

- Reusing the same config across many requests
- Updating thresholds centrally without changing request code
- Keeping per-project validator settings

```bash
# Create a stored config
POST /api/v1/guardrails/validators/configs/
  ?organization_id=1&project_id=101

# Use it in a request (server fetches config by ID)
{
  "validators": [{ "id": "your-config-uuid", "type": "pii_remover", ... }]
}
```

See [validators.md](validators.md) for each validator's config options.

---

## Multi-Tenant Design

Every request carries `organization_id` and `project_id`. Stored resources (ban lists, topic relevance configs, validator configs) are scoped to these identifiers. This means different teams or products can have completely different safety rules running on the same infrastructure.
