# gender_assumption_bias

Detects gendered language in LLM-generated text and replaces it with neutral alternatives. Targets assumption bias — language that implies a person's gender based on their role or profession.

---

## At a Glance

| Property | Value |
|----------|-------|
| Type | `gender_assumption_bias` |
| Implementation | Local (CSV-based lexical substitution) |
| Speed | Fast (< 20ms) |
| `fix_value` | Yes — returns text with neutral replacements applied |
| Requires API key | No |

---

## Configuration

```json
{
  "type": "gender_assumption_bias",
  "on_fail": "fix",
  "categories": ["all"]
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `categories` | `string[]` | `["all"]` | Which bias categories to check. See categories below. |
| `on_fail` | `string` | `"fix"` | `"fix"`, `"exception"`, or `"rephrase"` |

### Categories

| Category | What it addresses |
|----------|-----------------|
| `"generic"` | General gendered pronouns and terms ("he/she", "mankind", "chairman") |
| `"healthcare"` | Gendered assumptions about healthcare roles ("male nurse", "female doctor") |
| `"education"` | Gendered assumptions about teaching and student roles |
| `"all"` | All of the above (recommended) |

You can combine categories: `["healthcare", "education"]` applies only those two.

---

## How It Works Internally

1. **Bias list loading** — A CSV file containing columns `word`, `neutral-term`, and `type` (category) is loaded at initialization. The list is filtered by the configured categories. All terms are lowercased for case-insensitive matching.

2. **Matching** — For each entry in the bias list, a word-boundary regex (`\bword\b`) is applied to the input text using `re.IGNORECASE`. This ensures only whole-word matches, preventing partial substitutions inside longer words.

3. **Substitution** — Matched terms are replaced with their neutral counterparts. The substitution is applied in place, so multiple matches in the same text are all fixed in a single pass.

4. **Result** — If any substitution was made, returns `FailResult` with `fix_value` = the corrected text and an error message listing the detected biased words. Otherwise returns `PassResult`.

---

## Input / Output Examples

**Example 1 — Pronoun assumption:**
```
Input:  "Ask the nurse — she will help you register"
Output: "Ask the nurse — they will help you register"
```

**Example 2 — Role-based assumption:**
```
Input:  "The male nurse came in and the female doctor reviewed the chart"
Output: "The nurse came in and the doctor reviewed the chart"
```

**Example 3 — Generic gendered term:**
```
Input:  "This is a matter for all mankind to consider"
Output: "This is a matter for all humankind to consider"
```

**Example 4 — Multiple detections:**
```
Input:  "He or she should contact their chairman directly"
Output: "They should contact their chairperson directly"
```

**Example 5 — Clean text:**
```
Input:  "The doctor reviewed the patient's history"
Output: "The doctor reviewed the patient's history" (PassResult, no change)
```

---

## Common Pitfalls

### Substitution changes sentence flow
The validator substitutes terms exactly — it doesn't rewrite the sentence for grammatical flow. For example, replacing "he or she" with "they" works fine, but replacing "his" with "their" in `"his report"` → `"their report"` can sound slightly unnatural. Review output quality for your specific domain.

### Context-blind substitution
The matching is purely lexical. Words like "man" in "mangrove" or "woman" in "womanly" are protected by word boundaries, but edge cases in compound words may occur depending on the dataset.

### Lowercase replacement
The neutral term substitution is lowercased. If the original word was at the start of a sentence and capitalized, the replacement will be lowercase. Consider post-processing capitalization if this matters for your output quality.

### Coverage is dataset-dependent
The validator only catches terms present in the bias list CSV. Domain-specific gendered terms not in the list will pass through. You can extend coverage by contributing to the list.

---

## Recommended Stage

**Output** — Apply to LLM-generated responses before returning them to users. The validator corrects bias in what the model says, not what users ask.

---

## Pairing Recommendations

| Pair with | Why |
|-----------|-----|
| `pii_remover` | Common in healthcare/HR pipelines — remove PII and fix bias together |
| `llm_critic` with a bias metric | Use LLM critic to catch subtle contextual bias that the lexical approach misses |
