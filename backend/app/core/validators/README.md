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

Shared field:
- `on_fail` (default: `fix`)
  - `fix`: return redacted/neutralized output where possible
  - `exception`: fail validation without fix output
  - `rephrase`: use project-specific rephrase-on-fail behavior

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

## Validator Details

## 1) Lexical Slur Validator (`uli_slur_match`)

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
- Based on project notes, this aligns with NGO conversational safety requirements for multilingual abusive content.

Recommended stage:
- `input` and `output`
  - `input`: reduce harmful prompts/jailbreak-like toxic phrasing
  - `output`: prevent toxic wording in responses

Parameters / customization:
- `languages: list[str]` (default: `['en', 'hi']`)
- `severity: 'low' | 'medium' | 'high' | 'all'` (default: `'all'`)
- `on_fail`

Notes / limitations:
- Lexical matching can produce false positives in domain-specific contexts.
- Severity filtering is dependent on source slur list labels.
- Rules-based approach may miss semantic toxicity without explicit lexical matches.

Evaluation notes from project documentation:
- Dataset reference: `https://www.kaggle.com/c/multilingualabusivecomment/data`
- Label convention used in that dataset:
  - `1` = abusive comment
  - `0` = non-abusive comment
- Project notes call out acronym/context ambiguity (example: terms that can be abusive in one context but domain-specific neutral in another), so deployment-specific filtering is required.

## 2) PII Remover Validator (`pii_remover`)

Code:
- Config: `backend/app/core/validators/config/pii_remover_safety_validator_config.py`
- Runtime validator: `backend/app/core/validators/pii_remover.py`

What it does:
- Detects and anonymizes personally identifiable information using Presidio.
- Returns redacted text when PII is found and `on_fail=fix`.

Why this is used:
- Privacy is a primary safety requirement in NGO deployments.
- Project evaluation notes indicate need to prevent leakage/retention of user personal data in conversational flows.

Recommended stage:
- `input` and `output`
  - `input`: mask user-submitted PII before downstream processing/logging
  - `output`: prevent model responses from exposing personal details

Parameters / customization:
- `entity_types: list[str] | None` (default: all supported types)
- `threshold: float` (default: `0.5`)
- `on_fail`

Supported default entity types:
- `CREDIT_CARD`, `EMAIL_ADDRESS`, `IBAN_CODE`, `IP_ADDRESS`, `LOCATION`, `MEDICAL_LICENSE`, `NRP`, `PERSON`, `PHONE_NUMBER`, `URL`, `IN_AADHAAR`, `IN_PAN`, `IN_PASSPORT`, `IN_VEHICLE_REGISTRATION`, `IN_VOTER`

Notes / limitations:
- Rule/ML recognizers can under-detect free-text references.
- Threshold and entity selection should be tuned per deployment context.

Evaluation notes from project documentation:
- Compared approaches:
  - Custom PII validator (this codebase)
  - Guardrails Hub PII validator
- Dataset 1: `https://huggingface.co/datasets/ai4privacy/pii-masking-200k` (English subset in project evaluation)
  - Custom: Precision `0.614`, Recall `0.344`, F1 `0.441`
  - Hub: Precision `0.54`, Recall `0.33`, F1 `0.41`
- Dataset 2: synthetic Hindi dataset (project-created)
  - Reported results indicate tradeoffs by class, with the custom validator showing stronger balance for NGO deployment contexts where over-masking harms usability.

## 3) Gender Assumption Bias Validator (`gender_assumption_bias`)

Code:
- Config: `backend/app/core/validators/config/gender_assumption_bias_safety_validator_config.py`
- Runtime validator: `backend/app/core/validators/gender_assumption_bias.py`
- Data file: `backend/app/core/validators/utils/files/gender_assumption_bias_words.csv`

What it does:
- Detects gender-assumptive words/phrases and substitutes neutral terms.
- Uses a curated mapping from gendered terms to neutral alternatives.

Why this is used:
- Addresses model harm from assuming user gender or producing gender-biased language.
- Project documentation highlights this as a recurring conversational quality/safety issue.

Recommended stage:
- primarily `output`
  - safer default for response de-biasing
  - can also be used on `input` in stricter moderation pipelines

Parameters / customization:
- `categories: list[BiasCategories] | None` (default: `[all]`)
- `on_fail`

`BiasCategories` values:
- `generic`, `healthcare`, `education`, `all`

Notes / limitations:
- Rule-based substitutions may affect natural fluency.
- Gender-neutral transformation in Hindi/romanized Hindi can be context-sensitive.
- Full assumption detection often benefits from multi-turn context and/or LLM-as-judge approaches.

Improvement suggestions from project documentation:
- Strengthen prompt strategy so the model asks user preferences instead of assuming gendered terms.
- Fine-tune generation prompts for neutral language defaults.
- Consider external LLM-as-judge checks for nuanced multi-turn assumption detection.

## 4) Ban List Validator (`ban_list`)

Code:
- Config: `backend/app/core/validators/config/ban_list_safety_validator_config.py`
- Source: Guardrails Hub (`hub://guardrails/ban_list`)

What it does:
- Blocks or redacts configured banned words using the Guardrails Hub BanList validator.

Why this is used:
- Provides deployment-specific denylist control for terms that must never appear in inputs/outputs.
- Useful for policy-level restrictions not fully covered by generic toxicity detection.

Recommended stage:
- `input` and `output`

Parameters / customization:
- `banned_words: list[str]` (required)
- `on_fail`

Notes / limitations:
- Exact-list approach requires ongoing maintenance.
- Contextual false positives can occur for ambiguous terms.

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
