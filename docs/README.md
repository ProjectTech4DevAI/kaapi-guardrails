# Kaapi Guardrails — Developer Guide

A safety and moderation layer for LLM-powered applications. Kaapi Guardrails lets you chain validators over user inputs or model outputs before they reach production.

---

## Main Docs

Start here if you're new.

| Doc | What's inside |
|-----|--------------|
| [Getting Started](getting-started.md) | Install, configure, run your first validator in < 5 minutes |
| [Core Concepts](core-concepts.md) | Mental model: validators, pipelines, pass/fail, on-fail actions |
| [All Validators](validators.md) | All 10 validators — index, comparison table, individual deep dives |
| [Pipeline Design Patterns](pipeline-patterns.md) | Low-latency, high-precision, enterprise, and human-escalation pipelines |
| [Confidence & Decisioning](confidence-and-decisioning.md) | Thresholds, scores, block vs. escalate vs. rephrase |
| [Custom Validators](custom-validators.md) | Build your own: regex, API-backed, LLM-based |
| [Best Practices](best-practices.md) | Opinionated guidance from real deployments |
| [Common Use Cases](use-cases.md) | Customer support, enterprise assistants, social moderation, and more |
| [FAQ](faq.md) | Why did safe text get blocked? How do I reduce latency? |

---

## Deep Dives

For when you need to go further.

| Doc | What's inside |
|-----|--------------|
| [Evaluation & Benchmarking](deep-dives/evaluation.md) | Precision, recall, F1, latency — how validators are tested |
| [Architecture](deep-dives/architecture.md) | Request lifecycle, orchestration, DB logging, async patterns |
| [Debugging & Observability](deep-dives/debugging.md) | Validator traces, log inspection, replaying failed cases |

---

## Quick Reference

**Run a validation (POST /api/v1/guardrails/):**

```json
{
  "request_id": "2a6f6d5c-5b9f-4f6b-92e4-cf7d67f87932",
  "organization_id": 1,
  "project_id": 101,
  "input": "Your text here",
  "validators": [
    { "type": "pii_remover", "on_fail": "fix" },
    { "type": "uli_slur_match", "on_fail": "fix", "languages": ["en", "hi"] }
  ]
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "response_id": "d676f841-4579-4b73-bf8f-fe968af842f1",
    "rephrase_needed": false,
    "safe_text": "Your sanitized text here"
  }
}
```

**Available validators:** `uli_slur_match` · `pii_remover` · `gender_assumption_bias` · `ban_list` · `topic_relevance` · `llm_critic` · `llamaguard_7b` · `nsfw_text` · `profanity_free` · `answer_relevance_custom_llm`

**on_fail actions:** `fix` (default) · `exception` · `rephrase`
