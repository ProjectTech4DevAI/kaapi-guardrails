# pii_remover

Detects and anonymizes Personally Identifiable Information using [Microsoft Presidio](https://microsoft.github.io/presidio/). Includes India-specific entity types. Detected entities are replaced with structured placeholders like `[REDACTED_PERSON_1]`.

---

## At a Glance

| Property | Value |
|----------|-------|
| Type | `pii_remover` |
| Implementation | Local (Presidio + spaCy `en_core_web_lg`) |
| Speed | Fast–Medium (50–200ms depending on text length) |
| Languages | English (NLP engine); India-specific patterns via regex |
| `fix_value` | Yes — returns redacted text |
| Requires API key | No |

---

## Configuration

```json
{
  "type": "pii_remover",
  "on_fail": "fix",
  "entity_types": ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS"],
  "threshold": 0.5
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entity_types` | `string[]` | All 15 types | Which PII types to detect. Omit to check everything. |
| `threshold` | `float` | `0.5` | Minimum Presidio confidence score (0–1) to trigger redaction. Lower = more aggressive. |
| `on_fail` | `string` | `"fix"` | `"fix"`, `"exception"`, or `"rephrase"` |

---

## Supported Entity Types

| Entity Type | Example | Detection method |
|-------------|---------|-----------------|
| `PERSON` | "Priya Sharma" | spaCy NER |
| `PHONE_NUMBER` | "9876543210", "+91-98765-43210" | Regex + context |
| `EMAIL_ADDRESS` | "user@example.com" | Regex |
| `CREDIT_CARD` | "4111 1111 1111 1111" | Regex (Luhn check) |
| `IP_ADDRESS` | "192.168.1.1" | Regex |
| `LOCATION` | "Mumbai, Maharashtra" | spaCy NER |
| `URL` | "https://example.com/page" | Regex |
| `IBAN_CODE` | "DE89 3704 0044 0532 0130 00" | Regex |
| `MEDICAL_LICENSE` | Medical license number formats | Regex |
| `NRP` | National registration number | Regex |
| `IN_AADHAAR` | "2345 6789 0123" | Regex (12-digit format) |
| `IN_PAN` | "ABCDE1234F" | Regex (PAN format) |
| `IN_PASSPORT` | "A1234567" | Regex |
| `IN_VOTER` | Voter ID format | Regex |
| `IN_VEHICLE_REGISTRATION` | "MH 12 AB 1234" | Regex |

---

## Redaction Format

Detected entities are replaced with `[REDACTED_{ENTITY_TYPE}_{N}]` where `N` is a counter for multiple instances of the same type:

```
Input:  "Priya Sharma and Amit Gupta called 9876543210"
Output: "[REDACTED_PERSON_1] and [REDACTED_PERSON_2] called [REDACTED_PHONE_NUMBER_1]"
```

This format is:
- **Structured** — easy to parse programmatically
- **Informative** — tells you what type of PII was removed
- **Numbered** — disambiguates multiple instances

---

## How It Works Internally

1. **Analyzer initialization** — On first use, a spaCy `en_core_web_lg` NLP engine is built and cached globally. A Presidio `AnalyzerEngine` is constructed with this engine. India-specific recognizers (`InAadhaarRecognizer`, `InPanRecognizer`, etc.) are registered based on the configured `entity_types`.

2. **Analyzer caching** — Analyzer instances are cached by the set of India-specific recognizers in use. This means different `entity_types` combinations that share the same India recognizer set reuse the same analyzer.

3. **Analysis** — Presidio analyzes the text for the requested entity types. Each detection returns an entity type, position (start/end), and confidence score.

4. **Threshold filtering** — The default Presidio anonymizer filters results by the configured threshold. Entities with confidence below the threshold are not redacted.

5. **Anonymization** — `AnonymizerEngine` replaces detected spans with the `[REDACTED_...]` placeholders.

6. **Result** — If any entity was found and anonymized, returns `FailResult` with `fix_value` = the anonymized text. If no PII was found, returns `PassResult`.

---

## Input / Output Examples

**Example 1 — Multiple entity types:**
```
Input:  "Contact Amit Gupta at amit.gupta@corp.in or call +91-98765-43210"
Output: "Contact [REDACTED_PERSON_1] at [REDACTED_EMAIL_ADDRESS_1] or call [REDACTED_PHONE_NUMBER_1]"
```

**Example 2 — India-specific PII:**
```
Input:  "My Aadhaar is 2345 6789 0123 and PAN is ABCDE1234F"
Output: "My Aadhaar is [REDACTED_IN_AADHAAR_1] and PAN is [REDACTED_IN_PAN_1]"
```

**Example 3 — Restricting entity types:**
```json
{ "entity_types": ["CREDIT_CARD"] }

Input:  "Priya Sharma's card is 4111 1111 1111 1111"
Output: "Priya Sharma's card is [REDACTED_CREDIT_CARD_1]"
         (name NOT redacted — PERSON not in entity_types)
```

**Example 4 — No PII:**
```
Input:  "What is the weather in Mumbai today?"
Output: "What is the weather in Mumbai today?" (PassResult, no change)
         Note: "Mumbai" may be redacted if LOCATION is in entity_types
```

---

## Threshold Guidance

| Threshold | Behavior | When to use |
|-----------|----------|-------------|
| `0.3` | Aggressive — catches everything, more false positives on names/places | Healthcare, financial apps; high PII risk |
| `0.5` | Balanced — default for most use cases | General purpose |
| `0.7` | Conservative — precise, may miss ambiguous names | Internal tools with trusted users |

**Important:** Presidio's confidence scoring is per-entity-type. `PERSON` entities detected via spaCy NER typically score 0.85. India-specific regex patterns (`IN_AADHAAR`, `IN_PAN`) typically score 1.0 (exact regex match). Lowering the threshold primarily affects NER-based detections.

---

## Common Pitfalls

### LOCATION false positives
"Mumbai" or "India" may be detected as `LOCATION` and redacted, even in benign context. If you don't need location protection, omit `LOCATION` from `entity_types`.

### Short names and ambiguous tokens
Very short or common names (e.g., "Ali", "Sam") may not be detected by spaCy NER with high confidence. They'll pass through if their score is below threshold.

### Non-English text
The NLP engine is `en_core_web_lg` — English only. Hindi or other language names will not be detected by the NER component. India-specific regex recognizers (`IN_AADHAAR`, `IN_PAN`, etc.) work independently of language.

### First-run latency
The first request loads the spaCy model into memory. This can take 2–5 seconds. Subsequent requests use the cached model and are fast.

---

## Recommended Stage

**Both input and output** — Run on user inputs to prevent PII from reaching LLM APIs. Run on LLM outputs before returning to users to catch any PII the model may have reproduced or hallucinated.

**Always run before LLM calls** — Prevents sensitive data from being sent to OpenAI or other third-party APIs.

---

## Pairing Recommendations

| Pair with | Why |
|-----------|-----|
| Put `pii_remover` first in any pipeline | Redact before any LLM call |
| `ban_list` | Add specific sensitive terms not caught by Presidio (internal code names, project titles) |
