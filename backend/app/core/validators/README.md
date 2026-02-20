# Validator Configuration Guide

This document describes the validator configuration model used in this codebase, including the 4 currently supported validators from `backend/app/core/validators/validators.json`.

## Supported Validators

Current validator manifest:
- `uli_slur_match` (source: `local`)
- `pii_remover` (source: `local`)
- `gender_assumption_bias` (source: `local`)
- `ban_list` (source: `hub://guardrails/ban_list`)

## Configuration Model

All validator config classes inherit from `BaseValidatorConfig` in `backend/app/core/validators/config/base_validator_config.py`.

Shared fields:
- `on_fail` (default: `fix`)
  - `fix`: return transformed/redacted output when validator provides a fix
  - `exception`: fail validation when validator fails (no safe replacement output)
  - `rephrase`: return a user-facing rephrase prompt plus validator error details

At the Validator Config API layer (`/guardrails/validators/configs`), configs also include:
- `type`
- `stage`: `input` or `output`
- `on_fail_action` (mapped to runtime `on_fail`)
- `is_enabled`

## Runtime vs Stored Config

There are two config shapes used in this project:

1. Stored validator config (Config CRUD APIs)
- includes `stage`, `on_fail_action`, scope metadata, etc.

2. Runtime guardrail config (POST `/guardrails/`)
- validator objects are normalized before execution
- internal metadata like `stage`, ids, timestamps are removed
- `on_fail_action` is converted to `on_fail`

## On-Fail Actions

This project supports three `on_fail` behaviors at runtime:

- `fix`
  - Uses Guardrails built-in fix flow (`OnFailAction.FIX`).
  - If a validator returns `fix_value`, validation succeeds and API returns that transformed value as `safe_text`.
  - Typical outcome: redaction/anonymization/substitution without asking user to retry.

- `exception`
  - Uses Guardrails built-in exception flow (`OnFailAction.EXCEPTION`).
  - Validation fails without a fallback text; API returns failure (`success=false`) with error details.
  - Use when policy requires hard rejection instead of auto-correction.

- `rephrase`
  - Uses project custom handler `rephrase_query_on_fail`.
  - Returns: `"Please rephrase the query without unsafe content." + validator error message`.
  - API marks `rephrase_needed=true` when returned text starts with this prefix.
  - Useful when you want users to rewrite input instead of silently fixing it.

## How Recommendation Is Chosen

`stage` is always required in validator configuration (`input` or `output`).
The recommendation below is guidance on what to choose first, based on:
- where harm is most likely (`input`, `output`, or both),
- whether auto-fixes are acceptable for user experience,
- whether extra filtering at that stage creates too many false positives for the product flow.

## How These Recommendations Were Derived

These recommendations come from working with multiple NGOs to understand their GenAI WhatsApp bot use cases, reviewing real bot conversations/data, and then running a structured evaluation flow:
- NGO use-case discovery and conversation analysis:
  - Reviewed real conversational patterns, safety failure modes, and policy expectations across partner NGO workflows.
  - Identified practical risks to prioritize (harmful language, privacy leakage, bias, and deployment-specific banned terms).
- Curated validator-specific datasets:
  - Built evaluation and challenge datasets per validator from NGO use-case patterns and conversation analysis.
  - Included realistic multilingual/code-mixed and domain-specific examples that reflect actual bot usage contexts.
- Controlled experiments:
  - Compared validators and parameter settings across stages (`input` vs `output`).
  - Compared custom implementations against:
    - Guardrails Hub variants (prebuilt validators/packages from the Guardrails Hub ecosystem), where applicable.
    - Baseline alternatives (simpler/default checks used as reference points, such as minimal rule-based setups or prior/default configurations).
  - Tracked quality metrics (precision/recall/F1 where applicable) plus manual error review.
- Stress testing:
  - Used validator-specific stress-test datasets curated from NGO-inspired scenarios (adversarial phrasing, spelling variants, code-mixed text, and context-ambiguous examples).
  - Focused on false-positive/false-negative behavior and user-facing impact.
- Deployment-oriented tuning:
  - Converted findings into stage recommendations and default parameter guidance.
  - Prioritized NGO safety goals: reduce harmful content and privacy leakage while preserving usability.

## Validator Details

### 1) Lexical Slur Validator (`uli_slur_match`)

Code:
- Config: `backend/app/core/validators/config/lexical_slur_safety_validator_config.py`
- Runtime validator: `backend/app/core/validators/lexical_slur.py`
- Data file: `backend/app/core/validators/utils/files/curated_slurlist_hi_en.csv`

What it does:
- Detects lexical slurs using list-based matching.
- Normalizes text (emoji removal, encoding fix, unicode normalization, lowercase, whitespace normalization).
- Redacts detected slurs with `[REDACTED_SLUR]` when `on_fail=fix`.

Why this is used:
- Helps mitigate toxic/abusive language in user inputs and model outputs.
- Evaluation and stress tests showed this is effective for multilingual abusive-content filtering in NGO-style conversational flows.

Recommendation:
- `input` and `output`
  - Why `input`: catches abusive wording before it reaches prompt construction, logging, or downstream tools.
  - Why `output`: catches toxic generations that can still appear even with safe input.

Parameters / customization:
- `languages: list[str]` (default: `['en', 'hi']`)
- `severity: 'low' | 'medium' | 'high' | 'all'` (default: `'all'`)
- `on_fail`

Notes / limitations:
- Lexical matching can produce false positives in domain-specific contexts.
- Severity filtering is dependent on source slur list labels.
- Rules-based approach may miss semantic toxicity without explicit lexical matches.

Evidence and evaluation:
- Dataset reference: `https://www.kaggle.com/c/multilingualabusivecomment/data`
- Label convention used in that dataset:
  - `1` = abusive comment
  - `0` = non-abusive comment
- Experiments highlighted acronym/context ambiguity (example: terms abusive in one context but neutral in another), so deployment-specific filtering is required.

### 2) PII Remover Validator (`pii_remover`)

Code:
- Config: `backend/app/core/validators/config/pii_remover_safety_validator_config.py`
- Runtime validator: `backend/app/core/validators/pii_remover.py`

What it does:
- Detects and anonymizes personally identifiable information using Presidio.
- Returns redacted text when PII is found and `on_fail=fix`.

Why this is used:
- Privacy is a primary safety requirement in NGO deployments.
- Evaluation runs for this project showed clear risk of personal-data leakage/retention in conversational workflows without PII masking.

Recommendation:
- `input` and `output`
  - Why `input`: prevents storing or processing raw user PII in logs/services.
  - Why `output`: prevents model-generated leakage of names, numbers, or identifiers.

Parameters / customization:
- `entity_types: list[str] | None` (default: all supported types)
- `threshold: float` (default: `0.5`)
- `on_fail`

Threshold guidance:
- `threshold` is the minimum confidence score required for a detected entity to be treated as PII.
- Lower threshold -> more detections (higher recall, more false positives/over-masking).
- Higher threshold -> fewer detections (higher precision, more false negatives/missed PII).
- Start around `0.5`, then tune using real conversation samples by reviewing both missed PII and unnecessary masking.
- If the product is privacy-critical, prefer a slightly lower threshold and tighter `entity_types`; if readability is primary, prefer a slightly higher threshold.

Supported default entity types:
- `CREDIT_CARD`, `EMAIL_ADDRESS`, `IBAN_CODE`, `IP_ADDRESS`, `LOCATION`, `MEDICAL_LICENSE`, `NRP`, `PERSON`, `PHONE_NUMBER`, `URL`, `IN_AADHAAR`, `IN_PAN`, `IN_PASSPORT`, `IN_VEHICLE_REGISTRATION`, `IN_VOTER`

Notes / limitations:
- Rule/ML recognizers can under-detect free-text references.
- Threshold and entity selection should be tuned per deployment context.

Evidence and evaluation:
- Compared approaches:
  - Custom PII validator (this codebase)
  - Guardrails Hub PII validator
- Dataset 1: `https://huggingface.co/datasets/ai4privacy/pii-masking-200k` (English subset in project evaluation)
  - Custom: Precision `0.614`, Recall `0.344`, F1 `0.441`
  - Hub: Precision `0.54`, Recall `0.33`, F1 `0.41`
- Dataset 2: synthetic Hindi dataset (project-created)
  - Reported results indicate tradeoffs by class, with the custom validator showing stronger balance for NGO deployment contexts where over-masking harms usability.

### 3) Gender Assumption Bias Validator (`gender_assumption_bias`)

Code:
- Config: `backend/app/core/validators/config/gender_assumption_bias_safety_validator_config.py`
- Runtime validator: `backend/app/core/validators/gender_assumption_bias.py`
- Data file: `backend/app/core/validators/utils/files/gender_assumption_bias_words.csv`

What it does:
- Detects gender-assumptive words/phrases and substitutes neutral terms.
- Uses a curated mapping from gendered terms to neutral alternatives.

Why this is used:
- Addresses model harm from assuming user gender or producing gender-biased language.
- Evaluation reviews and stress tests identified this as a recurring conversational quality/safety issue.

Recommendation:
- primarily `output`
  - Why `output`: the assistant response is where assumption-biased phrasing is most likely to be emitted to end users.
  - Why not `input` by default: user text can be descriptive/quoted, so rewriting input can introduce false positives and intent drift.
  - Use `input` too when your policy requires strict moderation of user phrasing before any model processing.

Parameters / customization:
- `categories: list[BiasCategories] | None` (default: `[all]`)
- `on_fail`

`BiasCategories` values:
- `generic`, `healthcare`, `education`, `all`

Notes / limitations:
- Rule-based substitutions may affect natural fluency.
- Gender-neutral transformation in Hindi/romanized Hindi can be context-sensitive.
- Full assumption detection often benefits from multi-turn context and/or LLM-as-judge approaches.

Improvement suggestions from evaluation:
- Strengthen prompt strategy so the model asks user preferences instead of assuming gendered terms.
- Fine-tune generation prompts for neutral language defaults.
- Consider external LLM-as-judge checks for nuanced multi-turn assumption detection.

### 4) Ban List Validator (`ban_list`)

Code:
- Config: `backend/app/core/validators/config/ban_list_safety_validator_config.py`
- Source: Guardrails Hub (`hub://guardrails/ban_list`)

What it does:
- Blocks or redacts configured banned words using the Guardrails Hub BanList validator.

Why this is used:
- Provides deployment-specific denylist control for terms that must never appear in inputs/outputs.
- Useful for policy-level restrictions not fully covered by generic toxicity detection.

Recommendation:
- `input` and `output`
  - Why `input`: blocks prohibited terms before model invocation and tool calls.
  - Why `output`: enforces policy on generated text before it is shown to users.

Parameters / customization:
- `banned_words: list[str]` (optional if `ban_list_id` is provided)
- `ban_list_id: UUID` (optional if `banned_words` is provided)
- `on_fail`

Notes / limitations:
- Exact-list approach requires ongoing maintenance.
- Contextual false positives can occur for ambiguous terms.
- Runtime validation requires at least one of `banned_words` or `ban_list_id`.
- If `ban_list_id` is used, banned words are resolved from the tenant-scoped Ban List APIs.

## Example Config Payloads

Example: create validator config (stored shape)

```json
{
  "type": "pii_remover",
  "stage": "input",
  "on_fail_action": "fix",
  "is_enabled": true,
  "entity_types": ["PERSON", "PHONE_NUMBER", "IN_AADHAAR"],
  "threshold": 0.6
}
```

Example: runtime guardrail validator object (execution shape)

```json
{
  "type": "pii_remover",
  "on_fail": "fix",
  "entity_types": ["PERSON", "PHONE_NUMBER", "IN_AADHAAR"],
  "threshold": 0.6
}
```

## Operational Guidance

Default stage strategy:
- Input guardrails: `pii_remover`, `uli_slur_match`, `ban_list`
- Output guardrails: `pii_remover`, `uli_slur_match`, `gender_assumption_bias`, `ban_list`

Tuning strategy:
- Start with conservative defaults and log validator outcomes.
- Review false positives/false negatives by validator and stage.
- Iterate on per-validator parameters (`severity`, `threshold`, `categories`, `banned_words`).

## Related Files

- `backend/app/core/validators/validators.json`
- `backend/app/core/validators/config/base_validator_config.py`
- `backend/app/core/validators/config/ban_list_safety_validator_config.py`
- `backend/app/core/validators/config/pii_remover_safety_validator_config.py`
- `backend/app/core/validators/config/lexical_slur_safety_validator_config.py`
- `backend/app/core/validators/config/gender_assumption_bias_safety_validator_config.py`
- `backend/app/schemas/guardrail_config.py`
- `backend/app/schemas/validator_config.py`
