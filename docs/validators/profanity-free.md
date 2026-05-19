# profanity_free

Detects general profanity using a trained SVM classifier. A lightweight, fast check that complements the slur-specific `uli_slur_match` validator. Sourced from the Guardrails Hub.

---

## At a Glance

| Property | Value |
|----------|-------|
| Type | `profanity_free` |
| Implementation | Guardrails Hub (`hub://guardrails/profanity_free`) |
| Speed | Fast (< 50ms) |
| `fix_value` | No — no programmatic fix available |
| Requires API key | Guardrails Hub API key |

---

## Configuration

```json
{
  "type": "profanity_free",
  "on_fail": "exception"
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `on_fail` | `string` | `"fix"` | `"fix"`, `"exception"`, or `"rephrase"` |

No validator-specific configuration. The SVM model and word list are managed by the Guardrails Hub package.

---

## Important: `on_fail: "fix"` Behavior

`profanity_free` does **not** provide a `fix_value`. When `on_fail: "fix"` is configured and profanity is detected:

- `safe_text` will be `""` (empty string)
- The API response will include a `metadata.reason` field explaining which validator caused the empty output

**Use `"exception"` or `"rephrase"` instead of `"fix"` for this validator.** This is different from `uli_slur_match`, which does provide a redacted fix value.

```json
{ "type": "profanity_free", "on_fail": "exception" }
```

---

## Input / Output Examples

**Example 1 — Profanity detected, `on_fail: "exception"`:**
```
Input:  "This is absolute <profanity>"
Output: safe_text: null (exception raised)
```

**Example 2 — Profanity detected, `on_fail: "rephrase"`:**
```
Input:  "What the <profanity> is this?"
Output: "Please rephrase the query without unsafe content..."
        (rephrase_needed: true)
```

**Example 3 — Clean text:**
```
Input:  "Can you explain this concept to me?"
Output: "Can you explain this concept to me?" (PassResult)
```

---

## How It Differs from uli_slur_match

| | `profanity_free` | `uli_slur_match` |
|---|---|---|
| Detection method | SVM classifier | Lexical (CSV list) |
| Fix available | No | Yes (redacts slur) |
| Language | English-primary | English + Hindi |
| Coverage | General profanity | Specific slurs |
| Severity filtering | No | Yes (`low`/`medium`/`high`/`all`) |
| Multilingual | No | Yes (Hindi, Romanized) |

**Use both together** for broader coverage — `uli_slur_match` for Hindi and targeted slur detection, `profanity_free` as a general English profanity backstop.

---

## Common Pitfalls

### Empty output on `on_fail: "fix"`
If you forget to change from the default `"fix"` and profanity triggers, the output will be an empty string. Always use `"exception"` or `"rephrase"` for this validator.

### English-centric model
The SVM model is primarily trained on English profanity. Hindi or regional language profanity may not be detected. Use `uli_slur_match` for Hindi coverage.

### Context-blind classification
The SVM model operates at a word level. Profanity in clearly academic or citation contexts (e.g., "the paper analyzed the word '...'") may still trigger.

---

## Recommended Stage

**Input** — Catch profanity in user messages before they reach the LLM.

---

## Pairing Recommendations

| Pair with | Why |
|-----------|-----|
| `uli_slur_match` | Together they cover both slur database and general profanity |
| `nsfw_text` | For platforms that need both explicit language AND explicit content detection |
