# nsfw_text

Detects sexually explicit and NSFW (Not Safe For Work) content using a HuggingFace transformer model. Returns a confidence score per sentence or for the full text and blocks content above the configured threshold. Sourced from the Guardrails Hub.

---

## At a Glance

| Property | Value |
|----------|-------|
| Type | `nsfw_text` |
| Implementation | Guardrails Hub (`hub://guardrails/nsfw_text`) |
| Model | `textdetox/xlmr-large-toxicity-classifier` (default) |
| Speed | Medium (100–400ms on CPU, faster on GPU) |
| `fix_value` | No — no programmatic fix available |
| Requires API key | Guardrails Hub API key |

---

## Configuration

```json
{
  "type": "nsfw_text",
  "on_fail": "exception",
  "threshold": 0.8,
  "validation_method": "sentence",
  "device": "cpu"
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `threshold` | `float` | `0.8` | Confidence cutoff (0–1). Content scoring above this is flagged. |
| `validation_method` | `string` | `"sentence"` | `"sentence"` or `"full"`. See below. |
| `device` | `string` | `"cpu"` | `"cpu"` or `"cuda"` for GPU inference. |
| `model_name` | `string` | `"textdetox/xlmr-large-toxicity-classifier"` | HuggingFace model ID. |
| `on_fail` | `string` | `"fix"` | `"fix"`, `"exception"`, or `"rephrase"` |

---

## Important: `on_fail: "fix"` Behavior

`nsfw_text` does **not** provide a `fix_value`. When `on_fail: "fix"` is configured and NSFW content is detected:

- `safe_text` will be `""` (empty string)
- The API response `metadata.reason` will explain which validator caused this

**Use `"exception"` for this validator.** There is no safe automatic fix for NSFW content.

---

## `validation_method` Explained

### `"sentence"` (default)

The text is split into sentences. Each sentence is scored independently. If any single sentence exceeds the threshold, the validator fails.

**Use when:** NSFW content might be embedded within a longer, mostly-safe message. The `sentence` method catches it even if surrounding sentences are clean.

```
Input:  "Hello, how are you? [NSFW sentence here]. Thank you for your time."
Sentence scores: [0.01, 0.94, 0.02]
Result: FAIL (0.94 > threshold 0.8)
```

### `"full"`

The entire text is scored as a single unit.

**Use when:** You're evaluating short, single-intent texts where splitting by sentence isn't meaningful. Slightly faster than `"sentence"` mode.

```
Input:  "Hello, how are you? [NSFW sentence here]. Thank you for your time."
Full text score: 0.31 (averaged/mixed with safe content)
Result: PASS (0.31 < threshold 0.8)
```

**Implication:** `"full"` mode can miss NSFW content diluted within longer safe text. Prefer `"sentence"` for user-generated content.

---

## Threshold Guidance

| Threshold | Behavior |
|-----------|----------|
| `0.6` | Strict — flags borderline content; more false positives on mature-but-not-explicit content |
| `0.8` | Default — balanced for most moderation scenarios |
| `0.9` | Conservative — only catches high-confidence explicit content; fewer false positives |

For platforms with minors or strict content policies, use `0.6`. For general-purpose moderation, `0.8` is a reasonable starting point.

---

## Model: xlmr-large-toxicity-classifier

The default model (`textdetox/xlmr-large-toxicity-classifier`) is based on XLM-RoBERTa Large, fine-tuned for toxicity/NSFW classification. It supports 100+ languages, making it suitable for multilingual content.

**First-run note:** The model weights (~1.1GB) are downloaded on first use from HuggingFace Hub. Ensure your deployment has internet access or pre-download the model.

---

## Input / Output Examples

**Example 1 — NSFW sentence detected, `on_fail: "exception"`:**
```
Input:  "Let me tell you something. [NSFW content here]."
Sentence scores: [0.02, 0.96]
Output: safe_text: null (0.96 > threshold 0.8)
```

**Example 2 — NSFW in middle of longer text, sentence mode:**
```
Input:  "Good morning. [NSFW sentence]. Have a great day."
Sentence scores: [0.01, 0.92, 0.01]
Output: safe_text: null (sentence mode catches it)
```

**Example 3 — Same text in full mode:**
```
Full text score: 0.35 (diluted by safe sentences)
Output: "Good morning. [NSFW sentence]. Have a great day." (PASSES — missed!)
```

This illustrates why `"sentence"` mode is safer for user-generated content.

**Example 4 — Clean text:**
```
Input:  "Can you help me with my homework?"
Score: 0.01
Output: "Can you help me with my homework?" (PassResult)
```

---

## GPU Acceleration

For production deployments with high throughput requirements, set `"device": "cuda"` to run inference on GPU. This reduces per-request latency from ~200–400ms to ~20–50ms.

```json
{
  "type": "nsfw_text",
  "device": "cuda",
  "threshold": 0.8
}
```

Requires a CUDA-capable GPU and PyTorch with CUDA support installed.

---

## Common Pitfalls

### Model download on first request
The HuggingFace model is downloaded lazily on first use. In production, pre-warm the validator to avoid slow first requests and timeout errors.

### `on_fail: "fix"` returns empty string
There's no automatic way to "fix" NSFW content. Always use `"exception"` or `"rephrase"`.

### Multilingual content
The XLM-R model supports many languages but was primarily trained on English and European language data. Detection quality may vary for South Asian languages.

---

## Recommended Stage

**Input and Output** — Users may send explicit content; LLMs may also generate it unexpectedly.

---

## Pairing Recommendations

| Pair with | Why |
|-----------|-----|
| `uli_slur_match` | Slurs + explicit content are different risk vectors — cover both |
| `llamaguard_7b` with `no_sexual_content` | LlamaGuard provides a second opinion on borderline cases |
| Place before `topic_relevance` | No point running LLM topic checks on content you'll block anyway |
