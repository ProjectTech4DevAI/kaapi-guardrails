# Pipeline Design Patterns

Copy-paste pipelines for common deployment scenarios.

---

## Pattern 1: Low-Latency Moderation

**When to use:** High-volume consumer apps where response time is critical.

**Strategy:** Cheap, deterministic validators only. No LLM calls.

```json
{
  "validators": [
    {
      "type": "ban_list",
      "on_fail": "fix",
      "banned_words": ["competitor-x", "internal-project-name"]
    },
    {
      "type": "uli_slur_match",
      "on_fail": "fix",
      "languages": ["en", "hi"],
      "severity": "high"
    },
    {
      "type": "profanity_free",
      "on_fail": "fix"
    }
  ]
}
```

**Expected latency:** < 100ms  
**Coverage:** High-severity slurs, profanity, custom banned terms  
**Trade-off:** Misses nuanced cases (context-dependent harm, NSFW without explicit words)

---

## Pattern 2: High-Precision Public Platform

**When to use:** Social platforms, community tools, gaming chat. You need nuance but can afford a few hundred ms.

**Strategy:** Deterministic first, ML fallback, LLM critic for borderline content.

```json
{
  "validators": [
    {
      "type": "uli_slur_match",
      "on_fail": "exception",
      "languages": ["en", "hi"],
      "severity": "all"
    },
    {
      "type": "profanity_free",
      "on_fail": "fix"
    },
    {
      "type": "nsfw_text",
      "on_fail": "exception",
      "threshold": 0.8,
      "validation_method": "sentence"
    },
    {
      "type": "llamaguard_7b",
      "on_fail": "exception",
      "policies": ["no_violence_hate", "no_sexual_content", "no_encourage_self_harm"]
    }
  ]
}
```

**Expected latency:** 300–800ms  
**Coverage:** Slurs, profanity, NSFW, violence, hate speech, self-harm  
**Trade-off:** Higher cost per request; requires Guardrails Hub for LlamaGuard

---

## Pattern 3: Enterprise Compliance

**When to use:** Internal enterprise assistants, customer-facing tools with regulatory requirements, financial or legal products.

**Strategy:** PII protection + policy enforcement + audit trail. Hard blocks for anything PII-related.

```json
{
  "validators": [
    {
      "type": "pii_remover",
      "on_fail": "fix",
      "entity_types": [
        "PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS",
        "CREDIT_CARD", "IN_AADHAAR", "IN_PAN"
      ],
      "threshold": 0.5
    },
    {
      "type": "ban_list",
      "on_fail": "exception",
      "ban_list_id": "your-compliance-ban-list-uuid"
    },
    {
      "type": "topic_relevance",
      "on_fail": "rephrase",
      "topic_relevance_config_id": "your-domain-config-uuid",
      "llm_callable": "gpt-4o-mini"
    }
  ]
}
```

**Expected latency:** 500ms–2s (LLM call for topic relevance)  
**Coverage:** PII leakage, policy violations, off-domain queries  
**Trade-off:** LLM-based topic relevance adds latency and API cost

> Store your ban list and topic config using the management APIs so you can update them without code changes.

---

## Pattern 4: Domain-Specific Assistant with Quality Control

**When to use:** Healthcare chatbot, legal assistant, educational tool. You need to enforce topic scope AND validate response quality.

**Strategy:** Input validation for scope enforcement, output validation for quality.

**Input pipeline (before LLM):**

```json
{
  "validators": [
    {
      "type": "uli_slur_match",
      "on_fail": "exception",
      "languages": ["en", "hi"],
      "severity": "all"
    },
    {
      "type": "topic_relevance",
      "on_fail": "rephrase",
      "topic_relevance_config_id": "healthcare-scope-uuid",
      "llm_callable": "gpt-4o-mini"
    }
  ]
}
```

**Output pipeline (after LLM):**

```json
{
  "validators": [
    {
      "type": "pii_remover",
      "on_fail": "fix"
    },
    {
      "type": "gender_assumption_bias",
      "on_fail": "fix",
      "categories": ["healthcare"]
    },
    {
      "type": "llm_critic",
      "on_fail": "exception",
      "metrics": {
        "medical_safety": "The response should not provide specific medication dosages, diagnoses, or advice that requires a licensed physician. It should recommend consulting a doctor for medical decisions.",
        "groundedness": "The response should not make claims beyond what is generally known. No fabricated statistics or citations."
      },
      "max_score": 3,
      "llm_callable": "gpt-4o-mini"
    }
  ]
}
```

---

## Pattern 5: Human Escalation Workflow

**When to use:** Customer support, moderation queues, any workflow where borderline content needs human review.

**Strategy:** Combine `rephrase` (user-facing) with application-level score inspection.

```json
{
  "validators": [
    {
      "type": "uli_slur_match",
      "on_fail": "rephrase",
      "languages": ["en", "hi"],
      "severity": "medium"
    },
    {
      "type": "nsfw_text",
      "on_fail": "rephrase",
      "threshold": 0.6
    }
  ]
}
```

When `rephrase_needed: true` comes back:

```python
if response["data"]["rephrase_needed"]:
    # Prompt user to rewrite their message
    # Optionally: log to human review queue
    flag_for_human_review(request_id, original_input)
```

A lower threshold (e.g., `0.6` instead of `0.8`) means more borderline content gets flagged rather than silently passed. Tune this based on your false-positive tolerance.

---

## Ordering Principles

1. **Cheapest first.** Lexical/regex validators (< 10ms) before ML models (100–300ms) before LLM critics (500ms–2s).
2. **Hard blocks before soft fixes.** If you have an `exception` validator, put it early so you don't waste LLM time on content you'll block anyway.
3. **PII before LLM calls.** Redact sensitive information before sending text to any external LLM API.
4. **Domain scope before content quality.** No point evaluating response quality if the topic is off-scope.

---

## Mixing on_fail Actions

Different validators in the same pipeline can use different on_fail actions. This gives you flexibility:

```json
{
  "validators": [
    { "type": "pii_remover", "on_fail": "fix" },        // silently fix
    { "type": "uli_slur_match", "on_fail": "rephrase" }, // ask user to rewrite
    { "type": "llamaguard_7b", "on_fail": "exception" }  // hard block
  ]
}
```

If `llamaguard_7b` fires, the pipeline stops and returns an error. If only `uli_slur_match` fires, the user sees the rephrase prompt. If only `pii_remover` fires, the fixed text is returned silently.

The last on_fail that fires wins in terms of the response behavior.
