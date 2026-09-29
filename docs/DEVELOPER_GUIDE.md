# Kaapi Guardrails — Developer Guide

A safety and moderation layer for LLM-powered applications. Chain validators over user inputs or model outputs before they reach production.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Core Concepts](#2-core-concepts)
3. [Built-in Validators](#3-built-in-validators)
   - [Validator Index](#31-validator-index)
   - [uli_slur_match](#32-uli_slur_match)
   - [pii_remover](#33-pii_remover)
   - [gender_assumption_bias](#34-gender_assumption_bias)
   - [ban_list](#35-ban_list)
   - [profanity_free](#36-profanity_free)
   - [nsfw_text](#37-nsfw_text)
   - [llamaguard_7b](#38-llamaguard_7b)
   - [topic_relevance](#39-topic_relevance)
   - [llm_critic](#310-llm_critic)
   - [answer_relevance_custom_llm](#311-answer_relevance_custom_llm)
4. [Pipeline Design Patterns](#4-pipeline-design-patterns)
5. [Confidence Scores & Decisioning](#5-confidence-scores--decisioning)
6. [Custom Validators](#6-custom-validators)
7. [Best Practices](#7-best-practices)
8. [Common Use Cases](#8-common-use-cases)
9. [FAQ](#9-faq)
10. [Evaluation & Benchmarking](#10-evaluation--benchmarking)
11. [Architecture Deep Dive](#11-architecture-deep-dive)
12. [Debugging & Observability](#12-debugging--observability)

---

## 1. Getting Started

Get from zero to a running validation pipeline in under 5 minutes.

### What is Kaapi Guardrails?

Think of validators as automated reviewers that inspect user input or model output before it reaches production. You chain them together into a pipeline — the text passes through each validator in sequence, and each one can fix, block, or flag problems it finds.

**What it solves:**

- Toxic or abusive language reaching users
- PII (names, phone numbers, Aadhaar) leaking through LLM responses
- Biased or gendered language in AI outputs
- Jailbreaks and unsafe content
- Responses that drift off-topic
- Banned words slipping through

**Where it fits in your stack:**

```
User Input → [Guardrails Pipeline] → LLM → [Guardrails Pipeline] → User Response
                    ↓
            Validate, fix, block, or escalate
```

You can validate **inputs** (before the LLM sees them), **outputs** (before users see them), or both.

### Prerequisites

- Docker and Docker Compose
- `uv` for Python package management
- OpenAI API key (for LLM-based validators: `topic_relevance`, `llm_critic`, `answer_relevance_custom_llm`)
- Guardrails Hub API key (for hub validators: `ban_list`, `llamaguard_7b`, `nsfw_text`, `profanity_free`)

### Installation

**1. Clone and configure:**

```bash
git clone <repo-url>
cd kaapi-guardrails
cp .env.example .env
```

**2. Edit `.env` with your keys:**

```env
AUTH_TOKEN=your-bearer-token-here
OPENAI_API_KEY=sk-...
GUARDRAILS_HUB_API_KEY=your-guardrails-hub-key
POSTGRES_USER=app
POSTGRES_PASSWORD=changethis
POSTGRES_DB=app
```

**3. Start the services:**

```bash
# First-time setup: run migrations and seed data
docker compose --profile prestart up prestart

# Then start in development mode
docker compose watch
```

The API is now available at `http://localhost:8001`.

### Your First Validation

Send a request with a PII validator to scrub personal information:

```bash
curl -X POST "http://localhost:8001/api/v1/guardrails/" \
  -H "Authorization: Bearer your-bearer-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "organization_id": 1,
    "project_id": 1,
    "input": "Please contact Priya Sharma at priya@example.com or call 9876543210",
    "validators": [
      {
        "type": "pii_remover",
        "on_fail": "fix"
      }
    ]
  }'
```

**Expected response:**

```json
{
  "success": true,
  "data": {
    "response_id": "d676f841-4579-4b73-bf8f-fe968af842f1",
    "rephrase_needed": false,
    "safe_text": "Please contact [REDACTED_PERSON_1] at [REDACTED_EMAIL_ADDRESS_1] or call [REDACTED_PHONE_NUMBER_1]"
  },
  "error": null
}
```

### Chaining Multiple Validators

Validators run in the order you specify. The output of each becomes the input to the next.

```bash
curl -X POST "http://localhost:8001/api/v1/guardrails/" \
  -H "Authorization: Bearer your-bearer-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "550e8400-e29b-41d4-a716-446655440001",
    "organization_id": 1,
    "project_id": 1,
    "input": "Amit Gupta is an idiot, his number is 919611188278",
    "validators": [
      {
        "type": "pii_remover",
        "on_fail": "fix",
        "entity_types": ["PERSON", "PHONE_NUMBER"]
      },
      {
        "type": "uli_slur_match",
        "on_fail": "fix",
        "languages": ["en", "hi"],
        "severity": "all"
      }
    ]
  }'
```

### Understanding the Response

| Field | What it means |
|-------|--------------|
| `success` | `true` if the pipeline completed (even if validators triggered) |
| `safe_text` | The processed text after all validators ran. `null` if an `exception` on_fail fired |
| `rephrase_needed` | `true` if the `rephrase` on_fail action triggered — your app should prompt the user to rewrite their input |
| `error` | Set when `success: false` — describes what went wrong at the API level |

**When `safe_text` is null:** This happens when a validator is configured with `"on_fail": "exception"` and a violation is found. The pipeline stops and returns an error instead of a safe version of the text.

---

## 2. Core Concepts

### Validators

A **validator** is a function that takes text as input and returns either:

- **Pass** — text is safe, return it as-is (or with minor fixes)
- **Fail** — text violates a rule; apply the configured `on_fail` action

Each validator has a single responsibility. `pii_remover` does not check for toxicity. `uli_slur_match` does not redact phone numbers. Compose them together to build layered safety.

### The Validation Pipeline

Validators run **sequentially**, in the order you specify. The output of one validator becomes the input to the next.

```
Input Text
    │
    ▼
┌─────────────────┐
│  pii_remover    │  → fixes PII, passes redacted text forward
└────────┬────────┘
         │
    ▼
┌─────────────────┐
│ uli_slur_match  │  → checks redacted text for slurs, fixes if found
└────────┬────────┘
         │
    ▼
┌─────────────────┐
│  nsfw_text      │  → checks for NSFW content
└────────┬────────┘
         │
    ▼
 Safe Text (or null if exception fired)
```

**Order matters.** Run cheap, fast validators first. Run LLM-based validators last.

### On-Fail Actions

When a validator detects a violation, the `on_fail` setting controls what happens next.

| Action | Behavior | Use when |
|--------|----------|----------|
| `fix` (default) | Returns the corrected text (redacted, neutralized). If no fix is possible, returns empty string | You want the pipeline to continue with a cleaned version |
| `exception` | Halts the pipeline, returns `safe_text: null` and an error | You want a hard block — no output if the content is unsafe |
| `rephrase` | Returns a fixed message asking the user to rephrase | You want to signal the user to rewrite their input (e.g., for chatbots) |

**`rephrase` response example:**

```json
{
  "rephrase_needed": true,
  "safe_text": "Please rephrase the query without unsafe content..."
}
```

### Input vs. Output Validation

**Input validation** (before the LLM):
- Catches jailbreaks, abusive prompts, off-topic requests and PII in user queries
- Cheaper: stops bad prompts before spending LLM tokens
- Validators: `uli_slur_match`, `ban_list`, `topic_relevance`, `llamaguard_7b`, `pii_remover`

**Output validation** (after the LLM):
- Catches model hallucinations, biased language, toxic content
- Validates what users actually see
- Validators: `gender_assumption_bias`, `nsfw_text`, `llm_critic`, `answer_relevance_custom_llm`

Use the `stage` field when creating stored validator configs (`"stage": "input"` or `"stage": "output"`).

### Deterministic vs. LLM-Based Validators

| Type | Speed | Cost | Explainable | Nuanced | Examples |
|------|-------|------|------------|---------|---------|
| Lexical / regex | Fast | Free | Yes | No | `uli_slur_match`, `ban_list`, `profanity_free` |
| Embeddings / ML model | Fast | Low | Partial | Partial | `nsfw_text`, `llamaguard_7b` |
| LLM critic | Slow | Medium | Yes | Yes | `topic_relevance`, `llm_critic` |

**Rule of thumb:** Start with deterministic validators. Add LLM-based validators only for cases where context and nuance matter — and always put them last in the chain.

### Confidence Scores

Some validators return a confidence score alongside pass/fail:

- **`pii_remover`** — Presidio assigns a confidence score (0–1) per detected entity. The `threshold` config sets the minimum confidence required to redact.
- **`nsfw_text`** — HuggingFace transformer returns a probability score. The `threshold` config sets the cutoff.
- **`topic_relevance`** — LLM critic scores relevance 0–3. The pipeline fails if score < 2.
- **`llm_critic`** — Per-metric scores (0–`max_score`). Configurable threshold per metric.

Validators without scores (e.g., `uli_slur_match`, `ban_list`) are binary: match found or not.

### Stored Validator Configs

Rather than sending full validator configs in every request, you can store them in the database and reference them by ID:

```bash
# Create a stored config
POST /api/v1/guardrails/validators/configs/
  ?organization_id=1&project_id=101

# Use it in a request (server fetches config by ID)
{
  "validators": [{ "id": "your-config-uuid", "type": "pii_remover", ... }]
}
```

### Multi-Tenant Design

Every request carries `organization_id` and `project_id`. Stored resources (ban lists, topic relevance configs, validator configs) are scoped to these identifiers. Different teams or products can have completely different safety rules running on the same infrastructure.

---

## 3. Built-in Validators

### 3.1 Validator Index

10 validators across safety, privacy, quality, and compliance categories.

#### By Category

**Safety & Content Moderation**

| Validator | What it catches | Speed |
|-----------|----------------|-------|
| `uli_slur_match` | Slurs and abusive language (English + Hindi) | Fast |
| `profanity_free` | General profanity | Fast |
| `nsfw_text` | Sexually explicit / NSFW content | Medium |
| `llamaguard_7b` | Violence, hate, weapons, drugs, self-harm | Medium |

**Privacy**

| Validator | What it catches | Speed |
|-----------|----------------|-------|
| `pii_remover` | Names, phones, email, Aadhaar, PAN, and 11 more | Fast |

**Bias & Fairness**

| Validator | What it catches | Speed |
|-----------|----------------|-------|
| `gender_assumption_bias` | Gendered language — replaces with neutral terms | Fast |

**Policy & Compliance**

| Validator | What it catches | Speed |
|-----------|----------------|-------|
| `ban_list` | Your custom prohibited words and phrases | Fast |

**Quality & Relevance**

| Validator | What it catches | Speed |
|-----------|----------------|-------|
| `topic_relevance` | Off-topic queries outside configured domain scope | Slow (LLM) |
| `answer_relevance_custom_llm` | LLM answers that don't address the user's query | Slow (LLM) |
| `llm_critic` | Custom quality and safety metrics via LLM judge | Slow (LLM) |

#### Quick Comparison

| Validator | Type | Requires API key | `fix_value` available | Recommended `on_fail` |
|-----------|------|-----------------|----------------------|----------------------|
| `uli_slur_match` | Lexical | No | Yes (redacts slur) | `fix` or `exception` |
| `pii_remover` | NLP model | No | Yes (redacted text) | `fix` |
| `gender_assumption_bias` | Lexical | No | Yes (neutral text) | `fix` |
| `ban_list` | Lexical | Hub key | Yes (redacts word) | `exception` or `fix` |
| `profanity_free` | ML (SVM) | Hub key | No | `exception` or `rephrase` |
| `nsfw_text` | ML (Transformer) | Hub key | No | `exception` |
| `llamaguard_7b` | LLM (7B model) | Hub key | No | `exception` |
| `topic_relevance` | LLM critic | OpenAI key | No | `rephrase` |
| `answer_relevance_custom_llm` | LLM critic | OpenAI key | No | `exception` or `rephrase` |
| `llm_critic` | LLM critic | OpenAI key | No | `exception` |

> **`fix_value` available = No** means `on_fail: "fix"` will return an empty string when this validator triggers. Use `exception` or `rephrase` instead.

---

### 3.2 uli_slur_match

Detects abusive and hateful language using a curated slur database sourced from the ULI list. Supports English and Hindi, including Romanized and code-mixed text.

#### At a Glance

| Property | Value |
|----------|-------|
| Type | `uli_slur_match` |
| Implementation | Local (CSV-based lexical matching) |
| Speed | Fast (< 20ms) |
| Languages | English, Hindi (including Romanized) |
| `fix_value` | Yes — replaces matched slurs with `[REDACTED_SLUR]` |
| Requires API key | No |

#### Configuration

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

**Severity Levels**

Slurs in the database are tagged with severity `L` (low), `M` (medium), or `H` (high).

| Setting | Includes |
|---------|---------|
| `"low"` | L + M + H (catches everything, most false positives) |
| `"medium"` | M + H |
| `"high"` | H only (least false positives, misses mild terms) |
| `"all"` | Same as `"low"` — all severities |

Use `"all"` for public/community platforms. Use `"high"` if you're seeing too many false positives on technical or colloquial text.

#### How It Works Internally

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

#### Input / Output Examples

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

#### Common Pitfalls

- **Sarcasm and quotation** — The validator matches text literally. Quoting a slur (e.g., "He called me a \<slur\>") will still be flagged.
- **Code-mixed and regional variation** — The database covers Romanized Hindi but may not include every regional spelling variant or slang term. Evaluate on your specific corpus.
- **Normalization strips emojis first** — If a slur is expressed entirely through emoji characters, it will not be detected.
- **Word boundary matching** — A slur embedded inside a longer word (e.g., part of a URL) will not match. This reduces false positives on legitimate text.

#### Recommended Stage

**Input** — Run on user messages before they reach the LLM.

#### Pairing Recommendations

| Pair with | Why |
|-----------|-----|
| `profanity_free` | Covers general profanity beyond the slur database |
| `llamaguard_7b` with `no_violence_hate` | Catches hate speech that isn't a specific slur term |
| `ban_list` | Add domain-specific harmful terms not in the slur database |

---

### 3.3 pii_remover

Detects and anonymizes Personally Identifiable Information using [Microsoft Presidio](https://microsoft.github.io/presidio/). Includes India-specific entity types. Detected entities are replaced with structured placeholders like `[REDACTED_PERSON_1]`.

#### At a Glance

| Property | Value |
|----------|-------|
| Type | `pii_remover` |
| Implementation | Local (Presidio + spaCy `en_core_web_lg`) |
| Speed | Fast–Medium (50–200ms depending on text length) |
| Languages | English (NLP engine); India-specific patterns via regex |
| `fix_value` | Yes — returns redacted text |
| Requires API key | No |

#### Configuration

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

#### Supported Entity Types

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

Detected entities are replaced with `[REDACTED_{ENTITY_TYPE}_{N}]`:

```
Input:  "Priya Sharma and Amit Gupta called 9876543210"
Output: "[REDACTED_PERSON_1] and [REDACTED_PERSON_2] called [REDACTED_PHONE_NUMBER_1]"
```

#### How It Works Internally

1. **Analyzer initialization** — On first use, a spaCy `en_core_web_lg` NLP engine is built and cached globally. A Presidio `AnalyzerEngine` is constructed with this engine. India-specific recognizers are registered based on the configured `entity_types`.
2. **Analyzer caching** — Analyzer instances are cached by the set of India-specific recognizers in use.
3. **Analysis** — Presidio analyzes the text for the requested entity types. Each detection returns an entity type, position, and confidence score.
4. **Threshold filtering** — Entities with confidence below the threshold are not redacted.
5. **Anonymization** — `AnonymizerEngine` replaces detected spans with `[REDACTED_...]` placeholders.
6. **Result** — If any entity was found and anonymized, returns `FailResult` with `fix_value` = the anonymized text. Otherwise `PassResult`.

#### Input / Output Examples

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
Output: "Priya Sharma's card is [REDACTED_CREDIT_CARD_1]"  (name NOT redacted)
```

#### Threshold Guidance

| Threshold | Behavior | When to use |
|-----------|----------|-------------|
| `0.3` | Aggressive — catches everything, more false positives | Healthcare, financial apps |
| `0.5` | Balanced — default | General purpose |
| `0.7` | Conservative — precise, may miss ambiguous names | Internal tools with trusted users |

#### Common Pitfalls

- **LOCATION false positives** — "Mumbai" or "India" may be redacted in benign context. Omit `LOCATION` if you don't need it.
- **Short names** — Very short or common names (e.g., "Ali", "Sam") may score below threshold.
- **Non-English text** — The NLP engine is English-only. India-specific regex recognizers work independently of language.
- **First-run latency** — The first request loads the spaCy model (2–5 seconds). Warm up at startup in production.

#### Recommended Stage

**Both input and output** — Redact before LLM calls; also redact from LLM responses before returning to users.

---

### 3.4 gender_assumption_bias

Detects gendered language in LLM-generated text and replaces it with neutral alternatives. Targets assumption bias — language that implies a person's gender based on their role or profession.

#### At a Glance

| Property | Value |
|----------|-------|
| Type | `gender_assumption_bias` |
| Implementation | Local (CSV-based lexical substitution) |
| Speed | Fast (< 20ms) |
| `fix_value` | Yes — returns text with neutral replacements applied |
| Requires API key | No |

#### Configuration

```json
{
  "type": "gender_assumption_bias",
  "on_fail": "fix",
  "categories": ["all"]
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `categories` | `string[]` | `["all"]` | Which bias categories to check. |
| `on_fail` | `string` | `"fix"` | `"fix"`, `"exception"`, or `"rephrase"` |

**Categories:**

| Category | What it addresses |
|----------|-----------------|
| `"generic"` | General gendered pronouns and terms ("he/she", "mankind", "chairman") |
| `"healthcare"` | Gendered assumptions about healthcare roles ("male nurse", "female doctor") |
| `"education"` | Gendered assumptions about teaching and student roles |
| `"all"` | All of the above (recommended) |

You can combine: `["healthcare", "education"]` applies only those two.

#### How It Works Internally

1. A CSV file with columns `word`, `neutral-term`, and `type` (category) is loaded at initialization and filtered by the configured categories.
2. For each entry, a word-boundary regex (`\bword\b`) is applied using `re.IGNORECASE`.
3. Matched terms are replaced in-place with their neutral counterparts.
4. If any substitution was made, returns `FailResult` with `fix_value` = the corrected text.

#### Input / Output Examples

```
Input:  "Ask the nurse — she will help you register"
Output: "Ask the nurse — they will help you register"

Input:  "The male nurse came in and the female doctor reviewed the chart"
Output: "The nurse came in and the doctor reviewed the chart"

Input:  "He or she should contact their chairman directly"
Output: "They should contact their chairperson directly"
```

#### Common Pitfalls

- **Substitution changes sentence flow** — The validator substitutes terms exactly without grammatical rewriting. Review output quality for your domain.
- **Lowercase replacement** — Neutral terms are lowercase. Sentence-initial capitalization may be lost.
- **Coverage is dataset-dependent** — Only catches terms in the bias list CSV.

#### Recommended Stage

**Output** — Apply to LLM-generated responses before returning to users.

---

### 3.5 ban_list

Blocks or redacts a custom list of prohibited words, phrases, or patterns. Provide words inline or reference a stored ban list by ID. Sourced from the Guardrails Hub.

#### At a Glance

| Property | Value |
|----------|-------|
| Type | `ban_list` |
| Implementation | Guardrails Hub (`hub://guardrails/ban_list`) |
| Speed | Fast (< 10ms) |
| `fix_value` | Yes — redacts matched words |
| Requires API key | Guardrails Hub API key |

#### Configuration

**Mode 1: Inline word list**

```json
{
  "type": "ban_list",
  "on_fail": "fix",
  "banned_words": ["competitor-name", "internal-codename", "lawsuit"]
}
```

**Mode 2: Stored ban list (recommended for production)**

```json
{
  "type": "ban_list",
  "on_fail": "exception",
  "ban_list_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `banned_words` | `string[]` | Inline list of banned words or phrases |
| `ban_list_id` | `UUID` | ID of a stored ban list |
| `on_fail` | `string` | `"fix"`, `"exception"`, or `"rephrase"` |

> Provide exactly one of `banned_words` or `ban_list_id`.

#### Managing Stored Ban Lists

```bash
# Create
POST /api/v1/guardrails/ban_lists/
{ "name": "Competitor Terms", "words": ["CompetitorX", "RivalProduct"] }

# Update
PATCH /api/v1/guardrails/ban_lists/{id}

# List
GET /api/v1/guardrails/ban_lists/?organization_id=1&project_id=101

# Delete
DELETE /api/v1/guardrails/ban_lists/{id}
```

Changes take effect immediately for all subsequent requests.

#### Input / Output Examples

```
Input:  "I want a refund or I'll file a lawsuit"
(banned_words: ["lawsuit", "refund"], on_fail: "fix")
Output: "I want a  or I'll file a "

Input:  "Tell me about CompetitorX"
(ban_list_id: uuid, on_fail: "exception")
Output: safe_text: null
```

#### Common Pitfalls

- **Case sensitivity** — Matching is case-insensitive by default.
- **Substring matching** — Depending on the Hub implementation version, "ass" might affect "assistant". Test your word list.
- **Large inline lists** — If > 100 terms, prefer a stored ban list to avoid payload bloat.

#### Recommended Stage

**Input and Output** — Catch prohibited terms in user messages and in LLM responses.

---

### 3.6 profanity_free

Detects general profanity using a trained SVM classifier. A lightweight, fast check that complements `uli_slur_match`. Sourced from the Guardrails Hub.

#### At a Glance

| Property | Value |
|----------|-------|
| Type | `profanity_free` |
| Implementation | Guardrails Hub (`hub://guardrails/profanity_free`) |
| Speed | Fast (< 50ms) |
| `fix_value` | No — no programmatic fix available |
| Requires API key | Guardrails Hub API key |

#### Configuration

```json
{
  "type": "profanity_free",
  "on_fail": "exception"
}
```

No validator-specific configuration beyond `on_fail`.

#### Important: `on_fail: "fix"` Behavior

`profanity_free` does **not** provide a `fix_value`. When `on_fail: "fix"` is used and profanity is detected, `safe_text` will be `""` (empty string). **Always use `"exception"` or `"rephrase"` for this validator.**

#### How It Differs from uli_slur_match

| | `profanity_free` | `uli_slur_match` |
|---|---|---|
| Detection method | SVM classifier | Lexical (CSV list) |
| Fix available | No | Yes (redacts slur) |
| Language | English-primary | English + Hindi |
| Severity filtering | No | Yes |
| Multilingual | No | Yes (Hindi, Romanized) |

#### Common Pitfalls

- Empty output on `on_fail: "fix"` — always use `"exception"` or `"rephrase"` instead.
- English-centric — use `uli_slur_match` for Hindi coverage.
- Context-blind — profanity in academic/citation contexts may still trigger.

#### Recommended Stage

**Input** — Catch profanity in user messages before they reach the LLM.

---

### 3.7 nsfw_text

Detects sexually explicit and NSFW content using a HuggingFace transformer model (`textdetox/xlmr-large-toxicity-classifier`). Supports per-sentence or full-text scoring. Sourced from the Guardrails Hub.

#### At a Glance

| Property | Value |
|----------|-------|
| Type | `nsfw_text` |
| Implementation | Guardrails Hub (`hub://guardrails/nsfw_text`) |
| Model | `textdetox/xlmr-large-toxicity-classifier` (default) |
| Speed | Medium (100–400ms on CPU, faster on GPU) |
| `fix_value` | No — no programmatic fix available |
| Requires API key | Guardrails Hub API key |

#### Configuration

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
| `threshold` | `float` | `0.8` | Confidence cutoff (0–1). |
| `validation_method` | `string` | `"sentence"` | `"sentence"` (per-sentence) or `"full"` (entire text). |
| `device` | `string` | `"cpu"` | `"cpu"` or `"cuda"` for GPU inference. |
| `model_name` | `string` | `"textdetox/xlmr-large-toxicity-classifier"` | HuggingFace model ID. |
| `on_fail` | `string` | `"fix"` | Always use `"exception"` — no fix available. |

#### `validation_method` Explained

**`"sentence"` (default):** Each sentence is scored independently. If any sentence exceeds the threshold, the validator fails. Catches NSFW embedded within longer safe text.

**`"full"`:** The entire text is scored as one unit. Faster but can miss NSFW diluted by surrounding safe sentences.

```
Input:  "Good morning. [NSFW sentence]. Have a great day."
Sentence scores: [0.01, 0.92, 0.01] → FAIL (sentence mode)
Full text score:  0.35              → PASS (full mode, missed!)
```

Prefer `"sentence"` for user-generated content.

#### Threshold Guidance

| Threshold | Behavior |
|-----------|----------|
| `0.6` | Strict — more false positives on mature-but-not-explicit content |
| `0.8` | Default — balanced |
| `0.9` | Conservative — only high-confidence explicit content |

#### Common Pitfalls

- **Model download on first request** — ~1.1GB weights downloaded lazily. Pre-warm in production.
- **`on_fail: "fix"` returns empty string** — always use `"exception"`.
- **Multilingual** — XLM-R supports 100+ languages but was primarily trained on English/European data. Quality may vary for South Asian languages.

#### Recommended Stage

**Input and Output** — Users may send explicit content; LLMs may also generate it.

---

### 3.8 llamaguard_7b

Meta's LlamaGuard 7B model, fine-tuned for content safety classification across six policy categories. Returns binary safe/unsafe verdicts per policy. Sourced from the Guardrails Hub.

#### At a Glance

| Property | Value |
|----------|-------|
| Type | `llamaguard_7b` |
| Implementation | Guardrails Hub (`hub://guardrails/llamaguard_7b`) |
| Model | Meta LlamaGuard 7B |
| Speed | Medium (200–600ms depending on hardware) |
| `fix_value` | No — binary classification only |
| Requires API key | Guardrails Hub API key |

#### Configuration

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
| `on_fail` | `string` | `"fix"` | Always use `"exception"` — no fix available. |

#### Available Policies

| Policy | What it enforces | Examples of violations |
|--------|-----------------|----------------------|
| `no_violence_hate` | No violent content or hate speech | Calls to violence, dehumanizing language |
| `no_sexual_content` | No sexually explicit material | Pornographic descriptions |
| `no_criminal_planning` | No instructions for criminal activity | How to commit fraud, theft |
| `no_guns_and_illegal_weapons` | No content promoting illegal weapons | Instructions for illegal modifications |
| `no_illegal_drugs` | No harmful drug-related content | Instructions for manufacturing drugs |
| `no_encourage_self_harm` | No encouragement of self-harm | Content glorifying self-harm methods |

#### Policy Selection by Context

```json
// Public social platform
{ "policies": ["no_violence_hate", "no_sexual_content", "no_encourage_self_harm"] }

// NGO helpline
{ "policies": ["no_encourage_self_harm", "no_violence_hate"] }

// Youth/education platform
{ "policies": ["no_sexual_content", "no_illegal_drugs", "no_encourage_self_harm"] }
```

#### How It Compares

| | `uli_slur_match` | `nsfw_text` | `llamaguard_7b` |
|---|---|---|---|
| Approach | Lexical | ML classifier | Fine-tuned LLM |
| Policies | Slurs only | NSFW only | 6 distinct policies |
| Speed | Fastest | Medium | Medium-slow |
| Context-aware | No | Partially | Yes |

LlamaGuard understands the difference between "reporting on violence" and "inciting violence."

#### Input / Output Examples

```
Input:  "We should hurt all people who believe in X religion"
(policies: ["no_violence_hate"])
Result: FAIL — safe_text: null

Input:  "I've been feeling really hopeless lately, I don't want to be here anymore"
(policies: ["no_encourage_self_harm"])
Result: PASS — expression of distress, not encouragement of self-harm
```

#### Common Pitfalls

- **Model download on first use** — LlamaGuard 7B is a large model. Pre-warm in production.
- **Not a replacement for lexical validators** — Policy-level, not word-level. Use alongside `uli_slur_match`.
- **`on_fail: "fix"` gives empty string** — always use `"exception"`.

#### Recommended Stage

**Input and Output** — Catch policy violations in user messages and in LLM responses.

---

### 3.9 topic_relevance

Validates whether a user message falls within the configured topic scope, using an LLM-as-judge. Define "on-topic" in plain language — no training required.

#### At a Glance

| Property | Value |
|----------|-------|
| Type | `topic_relevance` |
| Implementation | Local (wraps Guardrails Hub `LLMCritic`) |
| Speed | Slow (500ms–2s, LLM API call) |
| `fix_value` | No |
| Requires API key | OpenAI API key |

#### Configuration

```json
{
  "type": "topic_relevance",
  "on_fail": "rephrase",
  "topic_relevance_config_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "llm_callable": "gpt-4o-mini"
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `topic_relevance_config_id` | `UUID` | required | ID of a stored topic relevance config |
| `llm_callable` | `string` | `"gpt-4o-mini"` | LLM model for evaluation |
| `prompt_schema_version` | `int` | `1` | Prompt template version |
| `on_fail` | `string` | `"fix"` | Use `"rephrase"` or `"exception"` — no fix available |

#### Setting Up a Topic Config

```bash
POST /api/v1/guardrails/topic_relevance_configs/

{
  "name": "Healthcare Assistant Scope",
  "configuration": "This assistant helps users with questions about symptoms, medications, preventive care, and general health information. It should NOT answer questions about cooking, sports, politics, or any topic unrelated to health."
}
```

Update without code changes: `PATCH /api/v1/guardrails/topic_relevance_configs/{id}`

#### How It Works Internally

1. Fetches the topic configuration string from the database.
2. Injects it into a versioned prompt template, instructing the LLM to score the input on a `scope_violation` metric.
3. Delegates to `LLMCritic` with `max_score=3` and `threshold=2`.
4. Score ≥ 2 → `PassResult`; Score < 2 → `FailResult`.
5. Uses JSON mode (`response_format: json_object`) when the LLM supports it.

#### Scoring

| Score | Meaning |
|-------|---------|
| 0 | Completely off-topic |
| 1 | Marginally related but not within scope |
| 2 | Partially within scope — passes |
| 3 | Clearly within scope — passes |

The threshold is fixed at 2 and cannot be configured.

#### Writing Effective Topic Configs

**Too narrow** (causes false positives):
```
"This assistant answers questions about diabetes."
```

**Well-calibrated:**
```
"This assistant supports users with questions about managing chronic conditions,
understanding lab reports, medication reminders, and preventive care.

Out of scope: cooking recipes, financial advice, legal matters, technology
support, entertainment, sports."
```

Tips: list out-of-scope topics explicitly; include 2–3 in-scope examples; test against 20+ inputs.

#### Input / Output Examples

```
Input:  "What are the side effects of metformin?"  → Score: 3 → PASS
Input:  "Who won the cricket World Cup in 2023?"   → Score: 0 → FAIL (rephrase)
Input:  "What foods should I eat to lose weight?"  → Score: 1 or 2 (tune your config)
```

#### Common Pitfalls

- **LLM non-determinism** — Borderline scores (≈1–2) may flip across calls. Calibrate your config to push scores clearly above or below the threshold.
- **Latency** — Every validation triggers an LLM API call. Put this last in your pipeline.
- **`on_fail: "fix"` returns empty string** — Use `"rephrase"` or `"exception"`.

#### Recommended Stage

**Input** — Enforce domain scope before the LLM processes the query.

---

### 3.10 llm_critic

A general-purpose LLM-as-judge. Define custom metrics with plain-language descriptions; the LLM scores the text on each. Use when no built-in validator covers your specific quality or safety requirement. Sourced from the Guardrails Hub.

#### At a Glance

| Property | Value |
|----------|-------|
| Type | `llm_critic` |
| Implementation | Guardrails Hub (`hub://guardrails/llm_critic`) |
| Speed | Slow (500ms–3s per request) |
| `fix_value` | No |
| Requires API key | OpenAI API key |

#### Configuration

```json
{
  "type": "llm_critic",
  "on_fail": "exception",
  "metrics": {
    "metric_name": "Plain-language rubric for this metric",
    "another_metric": "Description of another dimension"
  },
  "max_score": 3,
  "llm_callable": "gpt-4o-mini"
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `metrics` | `object` | Yes | Dict of `metric_name → description` |
| `max_score` | `int` | Yes | Maximum score per metric (e.g., 3) |
| `llm_callable` | `string` | Yes | LLM model for evaluation |
| `on_fail` | `string` | — | `"fix"`, `"exception"`, or `"rephrase"` |

**Default threshold:** approximately `max_score / 2`. With `max_score: 3`, a score of 1 fails, a score of 2 passes.

#### How to Write Good Metric Descriptions

Write as a clear rubric, not a vague label.

**Bad:**
```json
{ "quality": "Is this a good response?" }
```

**Good:**
```json
{
  "medical_safety": "Score 0–3. 0 = provides specific diagnoses or prescribes medications — only a licensed doctor should do this. 1 = borderline. 2 = appropriately general health information. 3 = clearly safe, recommends consulting a doctor."
}
```

#### Common Metric Templates

| Metric | Description example |
|--------|-------------------|
| `factual_accuracy` | "Only claims supported by well-established facts. No invented statistics or citations." |
| `groundedness` | "Stays within information provided in context. 0 if it adds outside information, 3 if fully grounded." |
| `medical_safety` | "Must not diagnose conditions, prescribe medications, or substitute for professional medical advice." |
| `tone` | "Professional, empathetic, and not dismissive or condescending." |
| `harmful_instructions` | "Does not provide instructions that could cause physical harm. 0=clearly harmful, 3=clearly safe." |

#### Input / Output Examples

```json
// Multiple metrics
{
  "metrics": {
    "groundedness": "Is the response supported by facts? 0=fabricated, 3=fully grounded.",
    "tone": "Is the tone professional? 0=dismissive, 3=professional and kind."
  },
  "max_score": 3
}

Input:  "My child has a fever, what should I do?"
→ LLM response: "Give 500mg of amoxicillin and call Dr. Sharma at +91-9812345678"

groundedness: 0 (fabricated doctor recommendation)
tone: 2 (reasonably kind)
Result: FAIL
```

#### `llm_critic` vs. `topic_relevance`

| | `topic_relevance` | `llm_critic` |
|---|---|---|
| Purpose | Scope enforcement | Custom quality/safety metrics |
| Config | Stored topic config | Inline metrics dict |
| Metrics | One fixed (`scope_violation`) | Any number, any dimension |
| When to use | "Is this question in scope?" | "Is this response good/safe?" |

#### Common Pitfalls

- **Non-deterministic scoring** — Design metrics so truly safe content scores 2–3 and unsafe content scores 0–1.
- **Prompt injection** — User input is included in the LLM prompt. Run deterministic validators first.
- **`on_fail: "fix"` returns empty string** — Use `"exception"` or `"rephrase"`.

#### Recommended Stage

**Output** — Evaluate LLM-generated responses before returning to users.

---

### 3.11 answer_relevance_custom_llm

Validates whether an LLM-generated answer is actually relevant to the user's query. Uses an LLM-as-judge with a configurable prompt template. Detects non-answers, deflections, and hallucinated responses that technically respond but don't address the question.

#### At a Glance

| Property | Value |
|----------|-------|
| Type | `answer_relevance_custom_llm` |
| Implementation | Local (LiteLLM-based) |
| Speed | Slow (500ms–2s, LLM API call) |
| `fix_value` | No |
| Requires API key | OpenAI API key |

#### Configuration

```json
{
  "type": "answer_relevance_custom_llm",
  "on_fail": "exception",
  "llm_callable": "gpt-4o-mini",
  "custom_prompt_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `llm_callable` | `string` | `"gpt-4o-mini"` | LLM model for evaluation |
| `prompt_template` | `string` | Default template | Inline template with `{query}` and `{answer}` placeholders |
| `custom_prompt_id` | `UUID` | — | ID of a stored custom prompt |
| `on_fail` | `string` | `"fix"` | Always use `"exception"` or `"rephrase"` — no fix available |

#### Critical: Input Format

Unlike all other validators, `answer_relevance_custom_llm` expects the `input` field to be a **JSON string** containing both the query and the answer:

```json
{
  "input": "{\"query\": \"What is the capital of France?\", \"answer\": \"Paris is the capital of France.\"}"
}
```

Your application must serialize the pair before sending:

```python
import json
guardrail_input = json.dumps({"query": user_query, "answer": llm_response})
```

Plain text input always fails immediately with a clear error message.

#### Default Prompt Template

```
Query: {query}
Answer: {answer}

Does the answer fully satisfy the query and constraints?
Answer only YES or NO.
```

- Response starts with `YES` → `PassResult`
- Response starts with `NO` → `FailResult`
- Any other response → `FailResult` (unexpected LLM output)

#### Managing Custom Prompts

```bash
# Create
POST /api/v1/guardrails/answer_relevance_prompts/
{
  "name": "Healthcare Relevance Check",
  "prompt_template": "Query: {query}\nAnswer: {answer}\n\nDoes the answer directly address the health question and recommend consulting a doctor when appropriate? Answer YES or NO."
}

# Update
PATCH /api/v1/guardrails/answer_relevance_prompts/{id}

# List
GET /api/v1/guardrails/answer_relevance_prompts/?organization_id=1&project_id=101
```

#### How It Works Internally

1. Parses the JSON string to extract `query` and `answer`. Returns `FailResult` immediately if malformed or either field is empty.
2. Formats the `prompt_template` with the values. Returns `FailResult` if a placeholder is missing.
3. Sends to the LLM via LiteLLM with `max_tokens=10`.
4. Strips and uppercases the response. Checks `.startswith("YES")` or `.startswith("NO")`.
5. Catches LLM API exceptions and returns them as `FailResult`.

#### Input / Output Examples

```
Input:  {"query": "How do I reset my password?", "answer": "Click 'Forgot Password', enter your email, follow the link."}
LLM:    "YES"
Result: PASS

Input:  {"query": "What are the side effects of ibuprofen?", "answer": "Ibuprofen is a common pain relief medication."}
LLM:    "NO" (doesn't address side effects)
Result: FAIL

Input:  "What is the capital of France?"  (plain text, not JSON)
Result: FAIL — "Input must be a JSON string with 'query' and 'answer' fields."
```

#### When to Use This Validator

Use it when:
- Your LLM sometimes deflects, goes off-topic, or gives generic non-answers
- You're building a RAG system and want to verify answers stay grounded to the query
- You have domain-specific relevance criteria

Don't use it for input validation (it requires both query AND answer), toxicity detection, or factual accuracy (use `llm_critic` with a `groundedness` metric for the latter).

#### `answer_relevance_custom_llm` vs. `llm_critic`

| | `answer_relevance_custom_llm` | `llm_critic` |
|---|---|---|
| Input format | JSON `{query, answer}` | Plain text |
| Evaluation | Binary YES/NO | Scored 0–max_score per metric |
| Use case | "Did the LLM answer the question?" | "How good/safe is the response?" |

#### Common Pitfalls

- **Input must be JSON** — The single most common mistake. Always serialize before sending.
- **Prompt template must contain `{query}` and `{answer}`** — Missing placeholders fail at runtime.
- **`on_fail: "fix"` returns empty string** — Use `"exception"` or `"rephrase"`.

#### Recommended Stage

**Output only** — Requires both the query and the answer; can only run after the LLM responds.

---

## 4. Pipeline Design Patterns

Copy-paste pipelines for common deployment scenarios.

### Pattern 1: Low-Latency Moderation

**When to use:** High-volume consumer apps where response time is critical.

**Strategy:** Cheap, deterministic validators only. No LLM calls.

```json
{
  "validators": [
    { "type": "ban_list", "on_fail": "fix", "banned_words": ["competitor-x"] },
    { "type": "uli_slur_match", "on_fail": "fix", "languages": ["en", "hi"], "severity": "high" },
    { "type": "profanity_free", "on_fail": "fix" }
  ]
}
```

**Expected latency:** < 100ms | **Trade-off:** Misses nuanced cases

### Pattern 2: High-Precision Public Platform

**When to use:** Social platforms, community tools, gaming chat.

```json
{
  "validators": [
    { "type": "uli_slur_match", "on_fail": "exception", "languages": ["en", "hi"], "severity": "all" },
    { "type": "profanity_free", "on_fail": "fix" },
    { "type": "nsfw_text", "on_fail": "exception", "threshold": 0.8, "validation_method": "sentence" },
    { "type": "llamaguard_7b", "on_fail": "exception", "policies": ["no_violence_hate", "no_sexual_content", "no_encourage_self_harm"] }
  ]
}
```

**Expected latency:** 300–800ms | **Trade-off:** Higher cost per request

### Pattern 3: Enterprise Compliance

**When to use:** Internal enterprise assistants, regulatory requirements.

```json
{
  "validators": [
    {
      "type": "pii_remover",
      "on_fail": "fix",
      "entity_types": ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD", "IN_AADHAAR", "IN_PAN"],
      "threshold": 0.5
    },
    { "type": "ban_list", "on_fail": "exception", "ban_list_id": "your-compliance-ban-list-uuid" },
    { "type": "topic_relevance", "on_fail": "rephrase", "topic_relevance_config_id": "your-domain-config-uuid" }
  ]
}
```

**Expected latency:** 500ms–2s | **Trade-off:** LLM cost for topic relevance

### Pattern 4: Domain-Specific Assistant with Quality Control

**Input pipeline (before LLM):**

```json
{
  "validators": [
    { "type": "uli_slur_match", "on_fail": "exception", "severity": "all" },
    { "type": "topic_relevance", "on_fail": "rephrase", "topic_relevance_config_id": "healthcare-scope-uuid" }
  ]
}
```

**Output pipeline (after LLM):**

```json
{
  "validators": [
    { "type": "pii_remover", "on_fail": "fix" },
    { "type": "gender_assumption_bias", "on_fail": "fix", "categories": ["healthcare"] },
    {
      "type": "llm_critic",
      "on_fail": "exception",
      "metrics": {
        "medical_safety": "Must not provide specific diagnoses or medication dosages. Should recommend consulting a doctor.",
        "groundedness": "No fabricated statistics or citations."
      },
      "max_score": 3,
      "llm_callable": "gpt-4o-mini"
    }
  ]
}
```

### Pattern 5: Human Escalation Workflow

```json
{
  "validators": [
    { "type": "uli_slur_match", "on_fail": "rephrase", "severity": "medium" },
    { "type": "nsfw_text", "on_fail": "rephrase", "threshold": 0.6 }
  ]
}
```

```python
if response["data"]["rephrase_needed"]:
    flag_for_human_review(request_id, original_input)
```

### Ordering Principles

1. **Cheapest first** — Lexical (< 10ms) → ML models (100–300ms) → LLM critics (500ms–2s)
2. **Hard blocks before soft fixes** — Don't waste LLM time on content you'll block anyway
3. **PII before LLM calls** — Redact before sending text to any external API
4. **Domain scope before content quality** — No point evaluating quality if the topic is off-scope

### Mixing on_fail Actions

```json
{
  "validators": [
    { "type": "pii_remover", "on_fail": "fix" },
    { "type": "uli_slur_match", "on_fail": "rephrase" },
    { "type": "llamaguard_7b", "on_fail": "exception" }
  ]
}
```

If `llamaguard_7b` fires, the pipeline stops with an error. If only `uli_slur_match` fires, the user sees a rephrase prompt. If only `pii_remover` fires, the fixed text is returned silently.

---

## 5. Confidence Scores & Decisioning

### How Confidence Works Per Validator

**Validators with confidence scores:**

- **`pii_remover`** — Presidio confidence (0–1) per entity. `threshold` = minimum to redact.
- **`nsfw_text`** — Transformer probability (0–1). `threshold` = cutoff.
- **`topic_relevance`** — LLM scores 0–3. Fails if score < 2.
- **`llm_critic`** — Per-metric score (0–`max_score`). Fails if any metric < `max_score/2`.

**Binary validators (no score):** `uli_slur_match`, `ban_list`, `profanity_free`, `gender_assumption_bias`, `llamaguard_7b`

### Threshold Tuning Guide

| Higher threshold | Lower threshold |
|-----------------|----------------|
| Fewer false positives (safe text incorrectly blocked) | More false positives |
| More false negatives (unsafe text passed) | Fewer false negatives |
| Better user experience | Stricter enforcement |

**Recommended starting points:**

| Validator | Conservative | Balanced | Strict |
|-----------|-------------|---------|--------|
| `pii_remover` | 0.7 | 0.5 | 0.3 |
| `nsfw_text` | 0.9 | 0.8 | 0.6 |

**Lower the threshold if** unsafe content is getting through. **Raise it if** users are complaining about blocked legitimate content. Always measure against a labeled dataset.

### Decisioning Patterns

**Hard block vs. soft escalation:**

```python
response = call_guardrails_api(input, validators=[...])

if not response["success"]:
    return block_response()

data = response["data"]

if data["safe_text"] is None:
    return block_response()          # exception on_fail fired

if data["rephrase_needed"]:
    return rephrase_prompt_response() # rephrase on_fail fired

return data["safe_text"]             # safe to use
```

### False Positives vs. False Negatives

| Error type | What it means | Cost |
|------------|--------------|------|
| **False positive** | Safe content blocked | User frustration, reduced utility |
| **False negative** | Unsafe content passed | Safety violation, harm, trust erosion |

- **Public-facing apps:** Tolerate more false positives. Block more aggressively.
- **Internal tools:** Can afford more false negatives.
- **Regulated contexts:** Near-zero false negatives required.

---

## 6. Custom Validators

### The Validator Interface

```python
from guardrails.validator_base import (
    FailResult, PassResult, ValidationResult, Validator, register_validator
)

@register_validator(name="my-custom-validator", data_type="string")
class MyCustomValidator(Validator):
    def validate(self, value: str, metadata: dict) -> ValidationResult:
        if violates_rule(value):
            return FailResult(
                error_message="Reason this failed",
                fix_value=cleaned_version(value),  # or None if no fix possible
            )
        return PassResult()
```

**`PassResult()`** — The text is safe. Pipeline continues.

**`FailResult(error_message, fix_value)`** — `fix_value` is required if `on_fail="fix"`. If `None`, the output becomes `""`.

### Example 1: Regex-Based Validator

```python
import re
from guardrails.validator_base import FailResult, PassResult, ValidationResult, Validator, register_validator

@register_validator(name="no-social-handles", data_type="string")
class NoSocialHandlesValidator(Validator):
    HANDLE_PATTERN = re.compile(r"@\w+")

    def validate(self, value: str, metadata: dict) -> ValidationResult:
        matches = self.HANDLE_PATTERN.findall(value)
        if matches:
            return FailResult(
                error_message=f"Social media handles found: {matches}",
                fix_value=self.HANDLE_PATTERN.sub("[HANDLE]", value),
            )
        return PassResult()
```

### Example 2: API-Backed Validator

```python
import httpx
from guardrails.validator_base import FailResult, PassResult, ValidationResult, Validator, register_validator

@register_validator(name="external-moderation", data_type="string")
class ExternalModerationValidator(Validator):
    def __init__(self, api_url: str, api_key: str, threshold: float = 0.8, **kwargs):
        self.api_url = api_url
        self.api_key = api_key
        self.threshold = threshold
        super().__init__(**kwargs)

    def validate(self, value: str, metadata: dict) -> ValidationResult:
        try:
            response = httpx.post(self.api_url, json={"text": value},
                                  headers={"Authorization": f"Bearer {self.api_key}"}, timeout=5.0)
            score = response.json()["toxicity_score"]
        except Exception as e:
            return FailResult(error_message=f"Validation service unavailable: {e}")

        if score >= self.threshold:
            return FailResult(error_message=f"Score {score:.2f} exceeds threshold {self.threshold}")
        return PassResult()
```

### Example 3: LLM-Based Validator

```python
from openai import OpenAI
from guardrails.validator_base import FailResult, PassResult, ValidationResult, Validator, register_validator

@register_validator(name="policy-check", data_type="string")
class PolicyCheckValidator(Validator):
    PROMPT = "Does the following text violate our policy of {policy}?\n\nText: {text}\n\nAnswer YES or NO only."

    def __init__(self, policy: str, llm_callable: str = "gpt-4o-mini", **kwargs):
        self.policy = policy
        self.client = OpenAI()
        self.model = llm_callable
        super().__init__(**kwargs)

    def validate(self, value: str, metadata: dict) -> ValidationResult:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": self.PROMPT.format(policy=self.policy, text=value)}],
            max_tokens=5,
        )
        if response.choices[0].message.content.strip().upper() == "YES":
            return FailResult(error_message=f"Policy violation: {self.policy}", fix_value=None)
        return PassResult()
```

### Wrapping in a Config

```python
from app.core.validators.config.base_validator_config import BaseValidatorConfig

class PolicyCheckConfig(BaseValidatorConfig):
    policy: str
    llm_callable: str = "gpt-4o-mini"

    def build(self):
        return PolicyCheckValidator(
            policy=self.policy,
            llm_callable=self.llm_callable,
            on_fail=self.resolve_on_fail(),
        )
```

Then register in `validators.json` and add the type to the `ValidatorType` enum.

### Common Patterns and Pitfalls

- **Always handle exceptions in `validate()`** — Network calls and model loading can raise. Unhandled exceptions propagate out of the pipeline.
- **Return a `fix_value` whenever possible** — When `on_fail="fix"` and `fix_value=None`, the output is an empty string. Always return a cleaned version instead.
- **Keep validators single-responsibility** — One validator, one concern. Combine focused validators in the pipeline.
- **LLM validators are slow — cache where possible** — LLM API calls take 500ms–2s. Cache at the application layer if the same input is validated frequently.

---

## 7. Best Practices

### Validator Design

- **Don't rely on a single validator** — Layer them: `uli_slur_match → ban_list → nsfw_text → llamaguard_7b`
- **Use deterministic checks before LLM calls** — Lexical/ML validators are 10–100x cheaper than LLM API calls
- **PII removal belongs at the start of input pipelines** — Redact before any LLM call

### Threshold Tuning

- **Start strict, then loosen** — Launch with `threshold=0.6`, tune after 2 weeks of real data
- **Never tune thresholds without data** — Collect labeled examples, run evaluation, then decide
- **Tune per use case** — A customer support bot and a public platform have different risk profiles

### Pipeline Configuration

- **Use stored configs for shared validator settings** — Update thresholds centrally without code changes
- **Separate input and output pipelines** — Different risk profiles, different optimal validators
- **Keep ban lists in the API** — Let compliance/legal teams update without deployments

### LLM Validators

- **Put LLM validators at the end of the chain** — Slowest and most expensive
- **Use `gpt-4o-mini` as default** — Fast and cheap; use `gpt-4o` only for critical nuanced evaluation
- **Test topic configs with diverse examples** — Too narrow frustrates users; too broad defeats the purpose

### Operations

- **Measure false positives continuously** — Weekly review of `outcome: FAIL` validator logs
- **Build a review queue for borderline content** — Route `rephrase_needed: true` to human review
- **Alert on sudden changes in block rate** — Spikes may indicate misconfiguration or new abuse patterns
- **Pre-warm ML models in production** — `nsfw_text` and `llamaguard_7b` load weights on first use

### Common Mistakes to Avoid

| Mistake | Better approach |
|---------|----------------|
| One giant catch-all pipeline for all use cases | Separate pipelines per product/use case |
| Using only `on_fail: exception` | Mix `fix` and `exception` |
| Tuning thresholds without a labeled dataset | Evaluate on real examples first |
| Sending PII to LLM APIs | Run `pii_remover` before any LLM call |
| Treating passing the pipeline as "definitely safe" | Validators reduce risk, they don't eliminate it |
| Shipping with default thresholds | They're starting points, not optimal values |

---

## 8. Common Use Cases

### Customer Support Bot

**Risks:** Abusive users, PII leakage in responses, off-topic queries.

**Input pipeline:**
```json
{
  "validators": [
    { "type": "uli_slur_match", "on_fail": "rephrase", "languages": ["en", "hi"], "severity": "all" },
    { "type": "ban_list", "on_fail": "rephrase", "ban_list_id": "support-ban-list-uuid" },
    { "type": "topic_relevance", "on_fail": "rephrase", "topic_relevance_config_id": "support-scope-uuid" }
  ]
}
```

**Output pipeline:**
```json
{
  "validators": [
    { "type": "pii_remover", "on_fail": "fix", "entity_types": ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD"] },
    { "type": "gender_assumption_bias", "on_fail": "fix", "categories": ["generic"] }
  ]
}
```

### NGO Helpline / Community Platform

**Priority:** Err heavily on the side of safety. False positives are acceptable.

```json
{
  "validators": [
    { "type": "uli_slur_match", "on_fail": "exception", "languages": ["en", "hi"], "severity": "all" },
    { "type": "nsfw_text", "on_fail": "exception", "threshold": 0.7 },
    { "type": "llamaguard_7b", "on_fail": "exception", "policies": ["no_violence_hate", "no_encourage_self_harm", "no_sexual_content"] },
    { "type": "pii_remover", "on_fail": "fix", "threshold": 0.4 }
  ]
}
```

Route `safe_text: null` responses to a crisis counselor or escalation workflow.

### Internal Enterprise Assistant

```json
{
  "validators": [
    { "type": "pii_remover", "on_fail": "fix", "entity_types": ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "IN_AADHAAR", "IN_PAN", "CREDIT_CARD"] },
    { "type": "ban_list", "on_fail": "exception", "ban_list_id": "internal-compliance-list-uuid" },
    { "type": "topic_relevance", "on_fail": "rephrase", "topic_relevance_config_id": "enterprise-scope-uuid" }
  ]
}
```

### Educational Chatbot (Students)

```json
{
  "validators": [
    { "type": "profanity_free", "on_fail": "fix" },
    { "type": "uli_slur_match", "on_fail": "exception", "languages": ["en", "hi"], "severity": "all" },
    { "type": "nsfw_text", "on_fail": "exception", "threshold": 0.6, "validation_method": "sentence" },
    { "type": "topic_relevance", "on_fail": "rephrase", "topic_relevance_config_id": "edu-scope-uuid" }
  ]
}
```

### Healthcare Assistant

**Input pipeline:**
```json
{
  "validators": [
    { "type": "uli_slur_match", "on_fail": "exception", "severity": "high" },
    { "type": "topic_relevance", "on_fail": "rephrase", "topic_relevance_config_id": "health-scope-uuid" }
  ]
}
```

**Output pipeline:**
```json
{
  "validators": [
    { "type": "pii_remover", "on_fail": "fix", "entity_types": ["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "MEDICAL_LICENSE"] },
    { "type": "gender_assumption_bias", "on_fail": "fix", "categories": ["healthcare"] },
    { "type": "llm_critic", "on_fail": "exception", "metrics": { "medical_safety": "Must not provide specific diagnoses, recommend specific medications, or substitute for professional medical advice." }, "max_score": 3 }
  ]
}
```

### Coding Copilot / Developer Tool

```json
{
  "validators": [
    { "type": "ban_list", "on_fail": "fix", "banned_words": ["password", "api_key", "secret", "private_key", "AWS_SECRET"] },
    { "type": "pii_remover", "on_fail": "fix", "entity_types": ["EMAIL_ADDRESS", "IP_ADDRESS", "PHONE_NUMBER"] }
  ]
}
```

For generated code output, add `llm_critic` with a security metric:
```json
{
  "type": "llm_critic",
  "metrics": { "security": "The generated code must not include hardcoded credentials, SQL injection vulnerabilities, or command injection patterns." },
  "max_score": 3
}
```

---

## 9. FAQ

### "Why was safe text blocked?"

**Threshold too low** — Raise `nsfw_text` or `pii_remover` threshold and re-run the specific input.

**Overly broad ban list** — A term appears in legitimate contexts. Review and narrow the entry.

**Topic config too narrow** — The LLM scored a reasonable query as off-topic. Revise to be more inclusive, test against 20+ examples.

**Slur/profanity false positive** — Raise `severity` from `"all"` to `"high"`.

**How to investigate:** Inspect `validator_log` — the `error` field tells you which validator fired and why.

### "Why use LLM critics if they're slow and expensive?"

LLM critics catch what rules can't. A slur filter doesn't understand sarcasm. A regex won't catch "subtle manipulation framing." Use them when:
- The difference between safe and unsafe depends on context
- You're validating the *quality* of a response, not just its content
- You need a custom policy that can't be expressed as a pattern

### "How do I reduce latency?"

1. Put cheap validators first (lexical < 10ms, ML 100–300ms, LLM 500ms–2s)
2. Use `gpt-4o-mini` over `gpt-4o` for LLM validators
3. Use `"validation_method": "full"` for `nsfw_text` if per-sentence isn't needed
4. Set `"device": "cuda"` for `nsfw_text` on GPU infrastructure
5. Narrow `entity_types` for `pii_remover` — detecting 3 types is faster than 15

### "Can validators run asynchronously?"

The current pipeline executes validators **synchronously and sequentially**. You can run multiple independent pipelines in parallel at the application layer.

### "How do I support multilingual moderation?"

- `uli_slur_match` — English + Hindi
- `pii_remover` — India-specific regex recognizers work language-independently
- `nsfw_text` — XLM-R model supports 100+ languages
- `llamaguard_7b` and `llm_critic` — Work in any language the underlying LLM supports
- `ban_list` — Matches strings exactly in any language or script

### "What's the difference between `fix` and `rephrase`?"

- **`fix`** silently corrects the text and returns the fixed version. The user doesn't know.
- **`rephrase`** returns a message asking the user to rewrite. Your app shows this prompt.

Use `fix` when you can automatically correct the issue (PII removal, bias). Use `rephrase` when you want the user to correct their input (abusive language, off-topic queries).

### "What happens if a validator crashes or the LLM API is down?"

The pipeline returns `success: false`. Decide whether to fail open (pass original text) or fail closed (block the request). For LLM validators, consider a fallback timeout: block rather than fail open.

### "How do I update my ban list or topic config without a deployment?"

```bash
PATCH /api/v1/guardrails/ban_lists/{id}
PATCH /api/v1/guardrails/topic_relevance_configs/{id}
```

Changes take effect immediately for all subsequent requests.

### "How do I test my pipeline before going to production?"

1. Build a labeled test set of safe and unsafe examples
2. Run each example through your pipeline
3. Compute precision, recall, and F1
4. Review false positives and false negatives manually
5. Adjust thresholds and repeat

Don't rely solely on the built-in evaluation datasets — they may not reflect your user base.

---

## 10. Evaluation & Benchmarking

### Why Accuracy Alone Is Misleading

An NSFW filter that blocks everything has 100% recall but 0% precision. A filter that blocks nothing has 100% precision but 0% recall. Always report both.

### Core Metrics

| Metric | Formula | What it measures |
|--------|---------|-----------------|
| **Precision** | TP / (TP + FP) | When we block, are we right? |
| **Recall** | TP / (TP + FN) | Of all unsafe content, what fraction do we catch? |
| **F1** | 2 × (P × R) / (P + R) | Harmonic mean |
| **False Positive Rate** | FP / (FP + TN) | How often do we block safe content? |

| Use case | Optimize for |
|----------|-------------|
| Public platform (social, gaming) | High recall — minimize misses |
| Enterprise internal tool | High precision — minimize false alarms |
| Healthcare / regulated | Near-perfect recall |
| General purpose | F1 — balanced |

### Running the Built-in Evaluations

```bash
python -m app.evaluation.pii.run
python -m app.evaluation.lexical_slur.run
python -m app.evaluation.gender_assumption_bias.run
python -m app.evaluation.ban_list.run
python -m app.evaluation.topic_relevance.run
python -m app.evaluation.toxicity.run
python -m app.evaluation.answer_relevance.run
```

Each script writes to `backend/app/evaluation/outputs/<validator>/`:
- `predictions.csv` — per-sample predictions
- `metrics.json` — precision, recall, F1 scores

### Evaluating on Your Own Data

**Step 1: Collect examples** — 100–500 real inputs: safe, unsafe, and borderline.

**Step 2: Label the examples:**
```csv
input,expected_outcome,notes
"What's the weather today?",pass,generic safe query
"<slur> you",fail,clear violation
```

**Step 3: Run through your pipeline:**
```python
import httpx, csv, uuid

results = []
with open("test_set.csv") as f:
    for row in csv.DictReader(f):
        response = httpx.post(
            "http://localhost:8001/api/v1/guardrails/",
            headers={"Authorization": "Bearer your-token"},
            json={"request_id": str(uuid.uuid4()), "organization_id": 1, "project_id": 1,
                  "input": row["input"], "validators": YOUR_VALIDATOR_CONFIG},
        ).json()
        predicted = "fail" if response["data"]["safe_text"] is None else "pass"
        results.append({"expected": row["expected_outcome"], "predicted": predicted})
```

**Step 4: Compute metrics:**
```python
from sklearn.metrics import precision_score, recall_score, f1_score

y_true = [1 if r["expected"] == "fail" else 0 for r in results]
y_pred = [1 if r["predicted"] == "fail" else 0 for r in results]
print(f"Precision: {precision_score(y_true, y_pred):.3f}")
print(f"Recall:    {recall_score(y_true, y_pred):.3f}")
print(f"F1:        {f1_score(y_true, y_pred):.3f}")
```

### Latency Benchmarking

```python
import time

latencies = []
for example in test_set:
    start = time.perf_counter()
    call_pipeline(example)
    latencies.append(time.perf_counter() - start)

print(f"p50: {sorted(latencies)[len(latencies)//2]*1000:.0f}ms")
print(f"p95: {sorted(latencies)[int(len(latencies)*0.95)]*1000:.0f}ms")
```

**Typical latency ranges:**

| Validator type | Expected latency |
|----------------|-----------------|
| Lexical (ban_list, uli_slur_match) | < 20ms |
| ML model (nsfw_text, llamaguard_7b) | 100–400ms |
| LLM critic (topic_relevance, llm_critic) | 500ms–3s |
| Combined pipeline (all types) | 1–5s |

### Datasets Used in Built-in Evaluations

| Validator | Dataset | Source |
|-----------|---------|--------|
| `uli_slur_match` | `lexical_slur_testing_dataset.csv` | ULI NGO database + synthetic |
| `pii_remover` | `pii_detection_testing_dataset.csv` | Project-created, India-context |
| `gender_assumption_bias` | `gender_bias_assumption_dataset.csv` | Project-created |
| `ban_list` | `ban_list_testing_dataset.csv` | Project-created |
| `topic_relevance` | `datasets/topic_relevance/` | Project-created, NGO scenarios |
| Toxicity | `datasets/toxicity/` | HASOC + project-created |
| `answer_relevance_custom_llm` | `SNEHA-answer-relevance-testing-dataset.csv` | Project-created |

### When to Re-evaluate

- After changing any threshold
- After updating a ban list or topic config
- After upgrading the guardrails-ai version
- Monthly, even without changes
- After any notable safety incident

---

## 11. Architecture Deep Dive

### High-Level Architecture

```
Client
  │
  │ POST /api/v1/guardrails/
  ▼
FastAPI Application (port 8001)
  │
  ├─ Authentication dependency (source IP + Bearer token -> tenant)
  │
  ├─ Config Resolution
  │    ├─ Fetch ban list words from DB (if ban_list_id provided)
  │    └─ Fetch topic config from DB (if topic_relevance_config_id provided)
  │
  ├─ Guard Building
  │    └─ Each ValidatorConfig.build() → guardrails Validator instance
  │
  ├─ Sequential Validation (guardrails-ai framework)
  │    ├─ Validator 1 → PassResult or FailResult
  │    ├─ Validator 2 → PassResult or FailResult
  │    └─ Validator N → PassResult or FailResult
  │
  ├─ Result Processing
  │    ├─ Extract safe_text from validated_output
  │    └─ Detect rephrase_needed (checks rephrase prefix)
  │
  └─ Audit Logging
       ├─ RequestLog (request + response metadata)
       └─ ValidatorLog (per-validator outcome)

PostgreSQL Database
  ├─ request_log
  ├─ validator_log
  ├─ ban_list / ban_list_item
  ├─ topic_relevance_config
  └─ validator_config
```

### Request Lifecycle

**1. Request parsing** — `GuardrailRequest` is parsed. The `type` field on each validator config routes to the correct config class via discriminated union.

**2. Config resolution** — For `ban_list_id` and `topic_relevance_config_id`, the actual data is fetched from the database before building the guard. This is why ban lists and topic configs can be updated without code changes.

**3. Guard building:**
```python
validators = [config.build() for config in validator_configs]
guard = Guard().use(*validators)
```

**4. Sequential validation:**
```python
result = guard.validate(input_text)
```
Each validator's output becomes the next validator's input.

- `on_fail="fix"`: `fix_value` is passed forward. Validation continues.
- `on_fail="exception"`: Pipeline stops. `safe_text` = `null`.
- `on_fail="rephrase"`: Fixed rephrase message set as output. Validation continues.

**5. Result processing:**
```python
if result.validated_output:
    safe_text = result.validated_output
    rephrase_needed = safe_text.startswith(REPHRASE_ON_FAIL_PREFIX)
else:
    safe_text = None  # exception fired
```

**6. Audit logging** — `request_log` (one row per request) and `validator_log` (one row per validator that ran). Pass logs are suppressed by default.

### Database Schema

**`request_log`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal log ID |
| `organization_id` | int | Tenant identifier |
| `project_id` | int | Project identifier |
| `request_id` | UUID | Client-provided request ID |
| `response_id` | UUID | Generated response ID |
| `status` | enum | `processing`, `success`, `error` |
| `request_text` | text | Original input |
| `response_text` | text | Processed output |

**`validator_log`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Internal log ID |
| `request_id` | UUID FK | Links to `request_log.id` |
| `name` | str | Validator type (e.g., `"pii_remover"`) |
| `input` | text | Text before this validator |
| `output` | text | Text after this validator |
| `error` | text | Error message if failed |
| `outcome` | enum | `PASS`, `FAIL` |

### API Routes Overview

| Route | Method | Description |
|-------|--------|-------------|
| `/api/v1/guardrails/` | POST | Run a validation pipeline |
| `/api/v1/guardrails/` | GET | List all validator types and schemas |
| `/api/v1/guardrails/validators/configs/` | POST/GET | Create / list stored validator configs |
| `/api/v1/guardrails/validators/configs/{id}` | GET/PATCH/DELETE | Manage a config |
| `/api/v1/guardrails/ban_lists/` | POST/GET | Create / list ban lists |
| `/api/v1/guardrails/ban_lists/{id}` | GET/PATCH/DELETE | Manage a ban list |
| `/api/v1/guardrails/topic_relevance_configs/` | POST/GET | Create / list topic configs |
| `/api/v1/guardrails/topic_relevance_configs/{id}` | GET/PATCH/DELETE | Manage a topic config |
| `/api/v1/guardrails/answer_relevance_prompts/` | POST/GET | Create / list answer relevance prompts |
| `/api/v1/guardrails/answer_relevance_prompts/{id}` | GET/PATCH/DELETE | Manage a prompt |

### Authentication

**Bearer token** (main guardrail endpoints): `Authorization: Bearer <token>`. Validated against SHA-256 hash of the plaintext `AUTH_TOKEN` env var.

**Source IP + tenant headers** (all endpoints except health check): the caller must appear in `ALLOWED_IPS`, and sends `X-ORGANIZATION-ID` / `X-PROJECT-ID` resolved by the Kaapi backend. These scope every read and write; tenant is never taken from the query string or body.

### Key Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AUTH_TOKEN` | Yes | Bearer token for main API |
| `OPENAI_API_KEY` | For LLM validators | Used by `topic_relevance`, `llm_critic`, `answer_relevance_custom_llm` |
| `GUARDRAILS_HUB_API_KEY` | For hub validators | Required for `ban_list`, `llamaguard_7b`, `nsfw_text`, `profanity_free` |
| `POSTGRES_*` | Yes | Database connection settings |
| `ALLOWED_IPS` | Yes in production | Comma-separated source IPs allowed to call this service |

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | FastAPI |
| ORM / data models | SQLModel + Pydantic v2 |
| Validator framework | guardrails-ai |
| PII detection | Microsoft Presidio |
| ML models | HuggingFace Transformers + PyTorch |
| LLM integration | OpenAI API via guardrails-ai / LiteLLM |
| Database | PostgreSQL + psycopg3 |
| Migrations | Alembic |
| Error tracking | Sentry |
| Package management | uv |
| Python version | 3.10–3.13 |

---

## 12. Debugging & Observability

### Reading Validator Logs

Every request produces a `validator_log` row for each validator that ran.

```sql
-- See all FAIL outcomes for a specific request
SELECT name, input, output, error, outcome
FROM validator_log
WHERE request_id = 'your-request-log-id'
ORDER BY inserted_at;
```

**Example FAIL log:**

```json
{
  "name": "nsfw_text",
  "input": "original text here",
  "output": null,
  "error": "NSFW content detected with confidence 0.87 (threshold: 0.80)",
  "outcome": "FAIL"
}
```

Pass logs are suppressed by default — you'll only see `FAIL` entries.

### Tracing a Request End-to-End

```sql
-- Step 1: Find the request log
SELECT id, request_id, status, request_text, response_text, inserted_at
FROM request_log
WHERE request_id = 'your-client-request-uuid';

-- Step 2: See each validator's outcome
SELECT name, outcome, error, input, output
FROM validator_log
WHERE request_id = (SELECT id FROM request_log WHERE request_id = 'your-client-request-uuid')
ORDER BY inserted_at;
```

**Tracing text transformation:**

```
Step 1: pii_remover
  Input:  "Priya Sharma called 9876543210"
  Output: "[REDACTED_PERSON_1] called [REDACTED_PHONE_NUMBER_1]"
  Outcome: FAIL (fix applied)

Step 2: uli_slur_match
  Input:  "[REDACTED_PERSON_1] called [REDACTED_PHONE_NUMBER_1]"
  Output: "[REDACTED_PERSON_1] called [REDACTED_PHONE_NUMBER_1]"
  Outcome: PASS
```

### Common Failure Patterns

| Symptom | Cause | Action |
|---------|-------|--------|
| `safe_text` is null | `exception` on_fail fired | Check `validator_log` error field |
| `rephrase_needed: true` | `rephrase` on_fail fired | Check which validator FAIL row triggered it |
| `safe_text` is empty string | `fix` on_fail fired with `fix_value=None` | Check for FAIL row where output is empty |
| Unsafe content still present | Threshold too high, or validator doesn't cover the pattern | Replay with lower threshold or additional validators |

### Replaying Failed Cases

```python
replay_request = {
    "request_id": str(uuid.uuid4()),
    "organization_id": 1,
    "project_id": 1,
    "input": original_input,  # from request_log.request_text
    "validators": [
        { "type": "nsfw_text", "threshold": 0.6, "on_fail": "exception" }
    ]
}
```

### Debugging Topic Relevance

1. Check the `error` field in `validator_log` — it contains the LLM's score
2. Read your config: `GET /api/v1/guardrails/topic_relevance_configs/{id}`
3. Revise if too narrow — add more example topics and explicit out-of-scope examples
4. Test the specific input manually

**Improving topic configs:**
```
Bad:    "This assistant is for healthcare questions."

Better: "This assistant helps with symptoms, medications, preventive care.
         Examples: 'What are symptoms of diabetes?', 'Is ibuprofen safe with blood pressure meds?'
         Out-of-scope: cooking, sports, technology, legal advice."
```

### Debugging PII Detection

If expected PII is not being redacted:
1. **Entity type not configured** — Check your `entity_types` list
2. **Threshold too high** — Try lowering to `0.3` to see if it fires
3. **Entity not in Presidio's types** — Consider a `ban_list` fallback
4. **Language/script mismatch** — Presidio performs best on Latin-script English

### Sentry Integration

Production errors are reported to Sentry (`SENTRY_DSN` env var). When a validator crashes:
- Exception captured with full stack trace
- Request returns `success: false`
- `request_log` entry updated to `status: error`

### Structured Log Output

```
INFO  request_id=... validator=pii_remover outcome=FAIL error="PERSON detected..."
INFO  request_id=... validator=uli_slur_match outcome=PASS
INFO  request_id=... response_id=... status=success latency_ms=234
```

Filter by `outcome=FAIL` to review blocked requests. Filter by `status=error` to review crashes.
