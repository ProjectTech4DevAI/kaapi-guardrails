# Confidence Scores & Decisioning

How validators report certainty, and how to use that to make better moderation decisions.

---

## How Confidence Works Per Validator

Not all validators return a numeric confidence score — some are binary.

### Validators with confidence scores

**`pii_remover` — Presidio confidence (0–1)**

Presidio assigns a confidence score to each detected entity. The `threshold` parameter controls the minimum score required to trigger redaction.

```json
{ "type": "pii_remover", "threshold": 0.7 }
```

- `threshold: 0.3` — Aggressively redacts; catches more, more false positives
- `threshold: 0.5` — Default; balanced
- `threshold: 0.7` — Conservative; precise but may miss edge cases

**`nsfw_text` — Transformer probability (0–1)**

The HuggingFace model returns a probability score for each sentence (or the full text). The `threshold` controls the cutoff.

```json
{ "type": "nsfw_text", "threshold": 0.8 }
```

**`topic_relevance` — LLM relevance score (0–3)**

The LLM critic scores the input 0–3 for how relevant it is to the configured topic. The pipeline fails if score < 2.

**`llm_critic` — Per-metric score (0–max_score)**

Each metric receives a score from 0 to `max_score`. The pipeline fails if any metric scores below approximately half of `max_score`.

### Binary validators (no score)

- `uli_slur_match` — match found or not
- `ban_list` — banned word found or not
- `profanity_free` — profanity detected or not
- `gender_assumption_bias` — gendered term found or not
- `llamaguard_7b` — safe or unsafe per policy

---

## Threshold Tuning Guide

### The fundamental tradeoff

| Higher threshold | Lower threshold |
|-----------------|----------------|
| Fewer false positives (safe text incorrectly blocked) | More false positives |
| More false negatives (unsafe text incorrectly passed) | Fewer false negatives |
| Better user experience | Stricter enforcement |

### Recommended starting points

| Validator | Conservative | Balanced | Strict |
|-----------|-------------|---------|--------|
| `pii_remover` | 0.7 | 0.5 | 0.3 |
| `nsfw_text` | 0.9 | 0.8 | 0.6 |

### When to adjust thresholds

**Lower the threshold if:** Unsafe content is getting through that you want blocked.  
**Raise the threshold if:** Users are complaining about legitimate content being blocked.

Always measure the impact of threshold changes against a labeled dataset. See [Evaluation & Benchmarking](deep-dives/evaluation.md).

---

## Decisioning Patterns

### Hard block vs. soft escalation

```python
# In your application layer
response = call_guardrails_api(input, validators=[...])

if not response["success"]:
    # Pipeline error — treat as block
    return block_response()

data = response["data"]

if data["safe_text"] is None:
    # exception on_fail fired — hard block
    return block_response()

if data["rephrase_needed"]:
    # rephrase on_fail fired — ask user to rewrite
    return rephrase_prompt_response()

# Safe to use
return data["safe_text"]
```

### Score-based routing

For validators that produce confidence scores (like `nsfw_text` or `pii_remover`), you can implement tiered responses at the application level by using different thresholds in separate pipeline configurations:

```python
# Conservative pipeline: threshold 0.6 — flag borderline cases
# Strict pipeline: threshold 0.9 — only block high-confidence cases

conservative_result = run_pipeline(input, threshold=0.6)
strict_result = run_pipeline(input, threshold=0.9)

if strict_result.blocked:
    # High confidence violation — hard block
    block()
elif conservative_result.blocked:
    # Borderline — escalate to human review
    escalate_to_human()
else:
    # Passed both — safe to use
    pass_through()
```

---

## False Positives vs. False Negatives

In safety systems, errors have asymmetric costs.

| Error type | What it means | Cost |
|------------|--------------|------|
| **False positive** | Safe content blocked | User frustration, reduced utility |
| **False negative** | Unsafe content passed | Safety violation, harm, trust erosion |

**For public-facing apps:** Tolerate more false positives. Block more aggressively.  
**For internal tools:** Can afford more false negatives. Reduce friction for trusted users.  
**For regulated contexts (healthcare, finance):** Near-zero false negatives required. Accept high false positives.

---

## Calibrating for Your Use Case

1. **Build a labeled dataset** of real inputs from your app — both safe and unsafe examples
2. **Run the dataset through your pipeline** at different thresholds
3. **Compute precision and recall** — see [Evaluation](deep-dives/evaluation.md)
4. **Plot precision-recall curve** — choose the threshold that meets your tolerance
5. **Recheck periodically** as user behavior evolves

A validator that performs well on public benchmarks may perform differently on your specific user base. Always evaluate on your own data.

---

## Interpreting Validator Logs

When debugging why content was blocked, inspect the validator logs:

```json
{
  "validator": "nsfw_text",
  "input": "original text",
  "output": null,
  "error": "NSFW content detected with confidence 0.87 (threshold: 0.80)",
  "outcome": "FAIL"
}
```

The `error` field describes which rule was violated and (where available) the score. See [Debugging & Observability](deep-dives/debugging.md).
