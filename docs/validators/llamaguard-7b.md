# llamaguard_7b

Meta's LlamaGuard 7B model, fine-tuned specifically for content safety classification across six policy categories. Returns binary safe/unsafe verdicts per policy. Sourced from the Guardrails Hub.

---

## At a Glance

| Property | Value |
|----------|-------|
| Type | `llamaguard_7b` |
| Implementation | Guardrails Hub (`hub://guardrails/llamaguard_7b`) |
| Model | Meta LlamaGuard 7B |
| Speed | Medium (200–600ms depending on hardware) |
| `fix_value` | No — binary classification only |
| Requires API key | Guardrails Hub API key |

---

## Configuration

```json
{
  "type": "llamaguard_7b",
  "on_fail": "exception",
  "policies": ["no_violence_hate", "no_sexual_content"]
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `policies` | `string[]` | All 6 policies | Which policies to enforce. Omit to enforce all. |
| `on_fail` | `string` | `"fix"` | `"fix"`, `"exception"`, or `"rephrase"` |

---

## Important: `on_fail: "fix"` Behavior

`llamaguard_7b` does **not** provide a `fix_value`. When `on_fail: "fix"` is configured and a policy violation is detected:

- `safe_text` will be `""` (empty string)

**Use `"exception"` for this validator.**

---

## Available Policies

| Policy | What it enforces | Examples of violations |
|--------|-----------------|----------------------|
| `no_violence_hate` | No violent content or hate speech targeting groups | Calls to violence, dehumanizing language about ethnic/religious groups |
| `no_sexual_content` | No sexually explicit material | Pornographic descriptions, explicit sexual scenarios |
| `no_criminal_planning` | No instructions for criminal activity | How to commit fraud, theft, stalking, or other crimes |
| `no_guns_and_illegal_weapons` | No content promoting illegal weapons | Instructions for illegal modifications, acquiring untraceable weapons |
| `no_illegal_drugs` | No harmful drug-related content | Instructions for manufacturing drugs, encouraging drug abuse |
| `no_encourage_self_harm` | No encouragement of self-harm or suicide | Content that glorifies or provides methods for self-harm |

Omit `policies` to enforce all six simultaneously.

---

## Selecting Specific Policies

You don't always need all six. Choose based on your deployment context:

**Public social platform:**
```json
{ "policies": ["no_violence_hate", "no_sexual_content", "no_encourage_self_harm"] }
```

**NGO helpline:**
```json
{ "policies": ["no_encourage_self_harm", "no_violence_hate"] }
```

**Youth/education platform:**
```json
{ "policies": ["no_sexual_content", "no_illegal_drugs", "no_encourage_self_harm"] }
```

**All-purpose high-stakes moderation:**
```json
{}
```
(omit `policies` to enforce all)

---

## How It Compares to Other Safety Validators

| | `uli_slur_match` | `nsfw_text` | `llamaguard_7b` |
|---|---|---|---|
| Approach | Lexical | ML classifier | Fine-tuned LLM |
| Policies | Slurs only | NSFW only | 6 distinct policies |
| Explanation | Which slur | Score | Which policy violated |
| Speed | Fastest | Medium | Medium-slow |
| Context-aware | No | Partially | Yes |
| Cost | Free | Hub key | Hub key |

LlamaGuard is context-aware in a way that lexical and simple ML classifiers are not. It understands the difference between "reporting on violence" and "inciting violence."

---

## Input / Output Examples

**Example 1 — Violence/hate speech:**
```json
{ "policies": ["no_violence_hate"], "on_fail": "exception" }

Input:  "We should hurt all people who believe in X religion"
Result: FAIL — no_violence_hate policy violated
Output: safe_text: null
```

**Example 2 — Self-harm content:**
```json
{ "policies": ["no_encourage_self_harm"], "on_fail": "exception" }

Input:  "I've been feeling really hopeless lately, I don't want to be here anymore"
Result: PASS — expression of distress, not encouragement of self-harm
        (LlamaGuard distinguishes between someone expressing crisis and content encouraging harm)
```

**Example 3 — Drug information (educational context):**
```json
{ "policies": ["no_illegal_drugs"], "on_fail": "exception" }

Input:  "What are the effects of methamphetamine on the brain?"
Result: PASS or FAIL depending on phrasing and context
        (LlamaGuard considers intent signals in the text)
```

**Example 4 — All policies, clean text:**
```
Input:  "Can you help me write a cover letter for a software engineering job?"
Result: PASS (all policies)
```

---

## Common Pitfalls

### Model download on first use
LlamaGuard 7B is a large model. The first request will download model weights. Pre-warm in production or expect a slow first request.

### Not a replacement for lexical validators
LlamaGuard won't catch every slur or profanity term — it's policy-level classification, not word-level matching. Use alongside `uli_slur_match` for complementary coverage.

### Context sensitivity can surprise you
LlamaGuard may pass content that looks superficially harmful because it understands context. An academic discussion of weapons policy is different from instructions for acquiring them. This is usually desirable, but test your specific use cases.

### `on_fail: "fix"` gives empty string
No fix is available. Use `"exception"` or `"rephrase"`.

---

## Recommended Stage

**Input** — Catch policy violations in user messages before they reach the LLM.  
**Output** — Also run on LLM outputs if the model might generate policy-violating content.

---

## Pairing Recommendations

| Pair with | Why |
|-----------|-----|
| `uli_slur_match` | LlamaGuard handles policy-level harm; slur matcher handles specific abusive terms |
| `nsfw_text` | Both cover sexual content but from different angles; complement each other |
| Run after fast validators | LlamaGuard is medium-slow — run `ban_list`/`uli_slur_match` first |
