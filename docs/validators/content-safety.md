# content_safety

Catches abusive language in English, Hindi and Romanised Hinglish. Runs the curated slur list (`uli_slur_match`) for word-level redaction, then a multilingual toxicity classifier for the whole message. A toxic message is replaced by your `fallback_message`.

---

## At a Glance

| Property | Value |
|----------|-------|
| Type | `content_safety` |
| Implementation | Local (`backend/app/core/validators/content_safety.py`) |
| Model | `textdetox/bert-multilingual-toxicity-classifier` (default, 178M, CPU) |
| Speed | Medium (~30 ms on CPU per message) |
| `fix_value` | Yes — redacted text for slur-only hits, `fallback_message` for toxic messages |
| Requires API key | No |

---

## Configuration

```json
{
  "type": "content_safety",
  "on_fail": "rephrase",
  "slur_severity": "all",
  "threshold": 0.5,
  "fallback_message": "Please rephrase your message without abusive language."
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `slur_severity` | `string` | `"all"` | `"low"`, `"medium"`, `"high"` or `"all"`. Minimum slur severity to redact. |
| `threshold` | `float` | `0.5` | Toxicity probability (0–1) at or above which the whole message is replaced. |
| `model_name` | `string` | `"textdetox/bert-multilingual-toxicity-classifier"` | Any HuggingFace text-classification model. |
| `toxic_label` | `string` | `"LABEL_1"` | Label the model emits for toxic text. |
| `fallback_message` | `string` | none | Returned in place of a toxic message. |
| `on_fail` | `string` | `"fix"` | `"fix"`, `"exception"`, or `"rephrase"` |

---

## How It Works

1. **Slur list.** Every listed slur is replaced by `[REDACTED_SLUR]`. Exact-string match, so it gives spans but misses variants (`madrachod`, `bhosdike`) and abuse with no slur.
2. **Classifier.** The original message is scored by the model. One score per message, no spans. At or above `threshold` the message is toxic as a whole.

The classifier scores the *original* text, not the redacted one. Redaction hides the signal: `tu chutiya hai bhag yahan se` scores 1.00, `tu [REDACTED_SLUR] hai bhag yahan se` scores 0.24.

| Slur hit | Model ≥ threshold | `on_fail: fix` returns | `on_fail: rephrase` returns |
|---|---|---|---|
| no | no | original text | original text |
| yes | no | redacted text | `fallback_message` (or rephrase prompt if unset) |
| any | yes | `fallback_message` (or `""` + `metadata.reason` if unset) | `fallback_message` (or rephrase prompt if unset) |

Use `rephrase` when the caller should see `rephrase_needed: true`. Use `fix` when the caller just forwards `safe_text`.

---

## Example

Request:

```json
{
  "request_id": "2a6f6d5c-5b9f-4f6b-92e4-cf7d67f87932",
  "input": "tu chutiya hai bhag yahan se",
  "validators": [
    {
      "type": "content_safety",
      "on_fail": "rephrase",
      "fallback_message": "Please rephrase your message without abusive language."
    }
  ]
}
```

Response:

```json
{
  "success": true,
  "data": {
    "response_id": "d676f841-4579-4b73-bf8f-fe968af842f1",
    "rephrase_needed": true,
    "safe_text": "Please rephrase your message without abusive language.",
    "validator_results": [
      {
        "name": "content-safety",
        "type": "content_safety",
        "order": 1,
        "outcome": "FAIL",
        "error": "Mentioned toxic words: chutiya; Toxic content detected (score 1.00)"
      }
    ]
  }
}
```

A message whose only problem is a listed slur keeps its redaction under `fix`: `Woh ladki randi hai` → `woh ladki [REDACTED_SLUR] hai`.

---

## Benchmark

1,801 rows (HASOC 200, ShareChat 1,000, lexical 601; en 727 / hi 1,074 incl. Romanised Hinglish), CPU. Details in [issue #181](https://github.com/ProjectTech4DevAI/kaapi-guardrails/issues/181).

| Config | Precision | Recall | F1 | Missed toxic |
|---|---|---|---|---|
| `uli_slur_match` alone | 0.90 | 0.63 | 0.74 | 416 |
| `profanity_free` alone | 0.78 | 0.23 | 0.36 | 873 |
| textdetox bert alone @0.5 | 0.79 | 0.83 | 0.81 | 194 |
| **`content_safety`** (slur OR textdetox @0.5) | 0.80 | **0.92** | **0.85** | **94** |

---

## Swapping the Model

No code change, just config. `toxic_label` differs per model.

```json
{ "type": "content_safety", "model_name": "textdetox/xlmr-large-toxicity-classifier", "toxic_label": "toxic" }
```

```json
{ "type": "content_safety", "model_name": "Hate-speech-CNERG/indic-abusive-allInOne-MuRIL", "toxic_label": "LABEL_1", "threshold": 0.4 }
```

| Model | Size | Our F1 (alone) | Notes |
|---|---|---|---|
| `textdetox/bert-multilingual-toxicity-classifier` | 178M | 0.81 | Default. en, hi, Hinglish. |
| `textdetox/xlmr-large-toxicity-classifier` | 560M | 0.80 | Same family, 3× size, no gain here. |
| `Hate-speech-CNERG/indic-abusive-allInOne-MuRIL` | 238M | 0.61 | Covers Tamil/Kannada/Bengali/Marathi; under-reads Romanised Hindi slurs. |

---

## Limitations

- **No word-level fix for toxicity.** The model returns one score per message. Only the slur list gives spans.
- **Tamil, Telugu, Kannada** are not in the default model's training data. Swap to MuRIL for Tamil/Kannada; no credible open CPU model for Telugu.
- **False alarms** are mostly heated political Devanagari and rude-but-harmless chat (~265 of 662 clean benchmark rows at 0.5). Raise `threshold` to 0.7 to cut ~50 of them for ~10% recall.
- **Memory.** The model is loaded once per process (~700 MB). The Docker image pre-downloads the default model.
- Slur redaction lowercases the text and strips emoji.
- `languages` is not accepted.
