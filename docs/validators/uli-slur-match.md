# uli_slur_match

Detects abusive and hateful language using a curated slur database sourced from the ULI list. Supports English and Hindi, including Romanized and code-mixed text.

---

## At a Glance

| Property | Value |
|----------|-------|
| Type | `uli_slur_match` |
| Implementation | Local (CSV-based lexical matching) |
| Speed | Fast (< 20ms) |
| Languages | English, Hindi (including Romanized) |
| `fix_value` | Yes — replaces matched slurs with `[REDACTED_SLUR]` |
| Requires API key | No |

---

## Configuration

```json
{
  "type": "uli_slur_match",
  "on_fail": "fix",
  "languages": ["en", "hi"],
  "severity": "all"
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `languages` | `string[]` | `["en", "hi"]` | Which language slur lists to load. Currently `"en"` and `"hi"` are supported. |
| `severity` | `string` | `"all"` | Minimum severity level to include. See severity levels below. |
| `on_fail` | `string` | `"fix"` | `"fix"`, `"exception"`, or `"rephrase"` |

### Severity Levels

Slurs in the database are tagged with severity `L` (low), `M` (medium), or `H` (high).

| Setting | Includes |
|---------|---------|
| `"low"` | L + M + H (catches everything, most false positives) |
| `"medium"` | M + H |
| `"high"` | H only (least false positives, misses mild terms) |
| `"all"` | Same as `"low"` — all severities |

**Recommendation:** Use `"all"` for public/community platforms. Use `"high"` if you're seeing too many false positives on technical or colloquial text.

---

## How It Works Internally

1. **Slur list loading** — At startup, reads a CSV file of slurs with columns `label` (the term) and `severity` (L/M/H). The list is filtered by the configured severity and cached in memory. The cache key is the severity string, so each severity level is loaded once per process lifetime.

2. **Text normalization** — Before matching, the input goes through a normalization pipeline:
   - Emojis removed (using the `emoji` library)
   - Encoding artifacts fixed (via `ftfy`)
   - Unicode normalized to NFKC form (handles ligatures, composed characters)
   - Lowercased
   - Whitespace collapsed

3. **Pattern compilation** — Each slur is compiled into a regex with word-boundary anchors (`(?<!\w)slur(?!\w)`), case-insensitive. Patterns are sorted longest-first to prevent shorter matches shadowing longer compound slurs.

4. **Matching** — The normalized text is scanned against all compiled patterns. Matches are collected.

5. **Redaction** — Each matched slur is replaced with `[REDACTED_SLUR]` in the normalized text. The redacted text is returned as `fix_value`.

---

## Input / Output Examples

**Example 1 — English slur with `on_fail: "fix"`:**
```
Input:  "Don't be such an <slur>, you know?"
Output: "Don't be such an [REDACTED_SLUR], you know?"
```

**Example 2 — Hindi slur (Romanized) with `on_fail: "exception"`:**
```
Input:  "Yeh banda bahut <hi-slur> hai"
Output: safe_text: null (exception raised)
```

**Example 3 — Mixed text, multiple slurs:**
```
Input:  "<slur1> and <slur2> both detected"
Output: "[REDACTED_SLUR] and [REDACTED_SLUR] both detected"
```

**Example 4 — Clean text:**
```
Input:  "Please help me with my application"
Output: "Please help me with my application" (PassResult, no change)
```

---

## Common Pitfalls

### Sarcasm and quotation
The validator matches text literally. `"He called me a <slur>"` (quoting someone else) will still be flagged. If your use case involves reporting harmful speech, consider a different flow.

### Code-mixed and regional variation
The database covers Romanized Hindi but may not include every regional spelling variant or slang term. Evaluate on your specific corpus to measure coverage.

### Normalization strips emojis first
If a slur is expressed entirely through emoji characters or emoji-text combinations, it will not be detected (emojis are removed before matching).

### Word boundary matching
The regex uses `(?<!\w)..(?!\w)` boundaries. A slur embedded inside a longer word (e.g., as part of a URL or technical term) will not match. This reduces false positives on legitimate text.

---

## Recommended Stage

**Input** — Run on user messages before they reach the LLM. Abusive inputs should be blocked or flagged at the entry point.

---

## Pairing Recommendations

| Pair with | Why |
|-----------|-----|
| `profanity_free` | Covers general profanity beyond the slur database |
| `llamaguard_7b` with `no_violence_hate` | Catches hate speech that isn't a specific slur term |
| `ban_list` | Add domain-specific harmful terms not in the slur database |
