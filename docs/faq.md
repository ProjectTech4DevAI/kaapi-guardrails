# FAQ

Answers to common questions.

---

## "Why was safe text blocked?"

This is the most common complaint. There are a few likely causes:

**1. Threshold too low**

If `nsfw_text` or `pii_remover` has a low threshold, borderline content gets flagged. Try raising the threshold and re-running the specific input.

**2. Overly broad ban list**

A term in your `ban_list` is appearing in legitimate contexts. Review your ban list and remove or narrow the entry.

**3. Topic relevance scope is too narrow**

Your topic config describes the scope too restrictively, and a reasonable on-topic question was scored as irrelevant by the LLM. Revise the config to be more inclusive. Test against 20+ representative examples.

**4. Slur/profanity false positive**

Some words are in the slur database but appear innocuously in your context (technical terms, names, transliterations). Raise the `severity` from `"all"` to `"high"`.

**How to investigate:**

Check the validator logs via the API:
```
GET /api/v1/guardrails/validators/configs/?organization_id=1&project_id=101
```
Or inspect the `validator_log` table directly. The `error` field will tell you which validator fired and why.

---

## "Why use LLM critics if they're slow and expensive?"

LLM critics catch what rules can't. A slur filter doesn't understand sarcasm. A regex won't catch "subtle manipulation framing." An LLM critic can evaluate intent, context, and nuance.

Use them when:
- You need to enforce a custom policy that can't be expressed as a pattern
- The difference between safe and unsafe depends on context
- You're validating the *quality* of a response, not just its content

Don't use them when:
- You only need to catch obvious violations (use lexical validators)
- Latency is critical (put them last, after fast validators)
- Cost is a hard constraint

---

## "How do I reduce latency?"

**1. Put cheap validators first.** Lexical validators (< 10ms) before ML models (100–300ms) before LLM critics (500ms–2s).

**2. Only validate what you need.** Don't run `llamaguard_7b` on every request if most of your traffic is safe. Consider running it only when faster validators pass a borderline score.

**3. Use `gpt-4o-mini` over `gpt-4o`** for LLM validators. It's 10x cheaper and about 2x faster for most moderation tasks.

**4. Use `"validation_method": "full"` for `nsfw_text`** if per-sentence granularity isn't needed. It's faster than `"sentence"` mode.

**5. GPU acceleration for ML models.** Set `"device": "cuda"` for `nsfw_text` if you have GPU-enabled infrastructure.

**6. Narrow your `entity_types` for `pii_remover`.** Detecting 15 PII types is slower than detecting 3. Only check for types you actually need.

---

## "Can validators run asynchronously?"

The current pipeline executes validators **synchronously and sequentially**. Each validator's output is the next validator's input, so true parallelism isn't possible within a single pipeline.

However, you can run multiple independent pipelines in parallel at the application layer — for example, running input and output validation concurrently in different requests.

---

## "How do I support multilingual moderation (beyond English and Hindi)?"

Currently, explicit multilingual support is available for English and Hindi via `uli_slur_match`. For other languages:

- `pii_remover` (Presidio) has some multilingual entity support — check Presidio's documentation for your language
- `nsfw_text` uses an XLM-R based model that supports 100+ languages
- `llamaguard_7b` and `llm_critic` work in any language the underlying LLM supports
- `ban_list` matches strings exactly — add terms in any language or script

For a language not covered by `uli_slur_match`, consider building a [custom validator](custom-validators.md) backed by a language-specific moderation API or dataset.

---

## "What's the difference between `fix` and `rephrase`?"

- **`fix`** silently corrects the text (redacts PII, replaces slurs) and returns the fixed version. The user doesn't know a correction happened.
- **`rephrase`** returns a message telling the user to rewrite their input. The `rephrase_needed: true` flag lets your app show a prompt to the user.

Use `fix` when you can automatically correct the issue without user involvement (PII removal, gender bias replacement).  
Use `rephrase` when you want the user to correct their input (abusive language, off-topic queries).

---

## "What happens if a validator crashes or the LLM API is down?"

The pipeline returns an error response with `success: false`. The `error` field describes what failed.

Your application should handle this gracefully — typically by deciding whether to fail open (pass the original text) or fail closed (block the request). The right choice depends on your risk tolerance.

For LLM-based validators, consider a fallback timeout strategy: if the LLM doesn't respond within N seconds, fail safe (block the request) rather than failing open.

---

## "How do I update my ban list or topic config without a deployment?"

Use the management APIs:

```bash
# Update ban list
PATCH /api/v1/guardrails/ban_lists/{id}

# Update topic relevance config
PATCH /api/v1/guardrails/topic_relevance_configs/{id}
```

These changes take effect immediately for all subsequent requests that reference the stored config ID.

---

## "How do I test my pipeline before going to production?"

1. Build a labeled test set of safe and unsafe examples representative of your user base
2. Run each example through your pipeline
3. Compute precision, recall, and F1 — see [Evaluation](deep-dives/evaluation.md)
4. Review false positives and false negatives manually
5. Adjust thresholds and validator configs based on findings
6. Repeat

Don't rely solely on the built-in evaluation datasets. They're useful for benchmarking validators in isolation but may not reflect your specific domain.
