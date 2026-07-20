# Best Practices

Opinionated guidance from real deployments.

---

## Validator Design

### Don't rely on a single validator

No single validator catches everything. A slur filter won't catch NSFW image-described content. A PII remover won't catch jailbreaks. Layer them.

```
uli_slur_match  →  ban_list  →  nsfw_text  →  llamaguard_7b
```

### Use deterministic checks before LLM calls

Lexical and ML validators are 10–100x cheaper than LLM API calls. Always gate on them first.

```
pii_remover (fast)  →  ban_list (fast)  →  topic_relevance (LLM)
```

If the fast validators block something, you never make the expensive LLM call.

### PII removal belongs at the start of input pipelines

Before you send any user text to an LLM, scrub PII. You don't want names, phone numbers, or Aadhaar numbers reaching a third-party API.

---

## Threshold Tuning

### Start strict, then loosen

When launching a new product, err on the side of more false positives. Users complaining about blocked legitimate content is recoverable. A safety incident is not.

```
Launch:  threshold=0.6  (strict)
After 2 weeks of data:  re-evaluate with real user examples
Production:  threshold=0.75  (tuned to your user base)
```

### Never tune thresholds without data

Don't adjust thresholds based on intuition. Collect a labeled dataset of real inputs, run evaluation, then decide. See [Evaluation & Benchmarking](deep-dives/evaluation.md).

### Tune per use case, not globally

A customer support bot and a public social platform have different risk profiles. Don't share threshold configs across wildly different deployments.

---

## Pipeline Configuration

### Use stored configs for shared validator settings

If multiple request paths use the same `pii_remover` config, create a stored validator config and reference it by ID. This means you can update thresholds centrally without touching request code.

### Separate input and output pipelines

Don't try to catch everything in one pipeline. Design separate pipelines for:
- Input validation (what the user sends to the LLM)
- Output validation (what the LLM sends back to the user)

They have different risk profiles and different optimal validators.

### Keep your ban lists in the API, not in code

Use `POST /api/v1/guardrails/ban_lists/` to create and manage ban lists. This lets compliance or legal teams update them without a code deployment.

---

## LLM Validators

### Put LLM validators at the end of the chain

They're the slowest and most expensive. Only run them if cheaper validators haven't already blocked the content.

### Use `gpt-4o-mini` as your default LLM callable

It's fast and cheap for most moderation tasks. Use `gpt-4o` only for complex, nuanced evaluation where accuracy is critical.

### Test your topic relevance configs with diverse examples

Write a topic relevance config that's too narrow and you'll frustrate users. Too broad and you defeat the purpose. Test against 20–30 representative examples before deploying.

---

## Operations

### Measure false positives continuously

Log and review blocked requests regularly. Set up a weekly review of `outcome: FAIL` validator logs. Look for patterns where legitimate content was blocked.

### Build a review queue for borderline content

When `rephrase_needed: true` or confidence is near-threshold, route to a human review queue. Especially important for regulated industries.

### Alert on sudden changes in block rate

A spike in blocks may mean your validator config is misconfigured, or a new type of abuse is emerging. A sudden drop may mean a validator stopped working.

```python
# Example monitoring metric
block_rate = failed_requests / total_requests
if block_rate > 0.1:  # > 10% of requests being blocked
    send_alert("High guardrail block rate detected")
```

### Pre-warm ML models in production

`nsfw_text` and `llamaguard_7b` load ML model weights on first use. In production, warm them up at startup to avoid slow first requests.

---

## Common Mistakes to Avoid

| Mistake | Better approach |
|---------|----------------|
| One giant catch-all pipeline for all use cases | Separate pipelines per product/use case |
| Using only `on_fail: exception` | Mix `fix` and `exception` — not every violation needs a hard block |
| Tuning thresholds without a labeled dataset | Evaluate on real examples first |
| Sending PII to LLM APIs | Run `pii_remover` before any LLM call |
| Treating passing the pipeline as "definitely safe" | Validators reduce risk, they don't eliminate it. Layer with application-level logic |
| Shipping with default thresholds | They're starting points, not optimal values for your use case |
