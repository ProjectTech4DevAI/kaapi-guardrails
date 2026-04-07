# Validator Configuration Guide

This document describes the validator configuration model used in this codebase, including the currently supported validators from `backend/app/core/validators/validators.json`.

## Supported Validators

Current validator manifest:

- `uli_slur_match` (source: `local`)
- `pii_remover` (source: `local`)
- `gender_assumption_bias` (source: `local`)
- `ban_list` (source: `hub://guardrails/ban_list`)
- `llm_critic` (source: `hub://guardrails/llm_critic`) - https://guardrailsai.com/hub/validator/guardrails/llm_critic
- `topic_relevance` (source: `local`)
- `llamaguard_7b` (source: `hub://guardrails/llamaguard_7b`)
- `profanity_free` (source: `hub://guardrails/profanity_free`)
- `nsfw_text` (source: `hub://guardrails/nsfw_text`)

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
- Runtime requirement: this validator is configured to use spaCy model `en_core_web_lg`.
  The model is pre-installed at build time in the Docker image to ensure fast startup and no runtime internet dependency.
  For local development without Docker, manually install the model using: `python -m spacy download en_core_web_lg`
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

### 5) LLM Critic Validator (`llm_critic`)

Code:

- Config: `backend/app/core/validators/config/llm_critic_safety_validator_config.py`
- Source: Guardrails Hub (`hub://guardrails/llm_critic`) — https://guardrailsai.com/hub/validator/guardrails/llm_critic

What it does:

- Evaluates text against one or more custom quality/safety metrics using an LLM as judge.
- Each metric is scored up to `max_score`; validation fails if any metric score falls below the threshold.

Why this is used:

- Enables flexible, prompt-driven content evaluation for use cases not covered by rule-based validators.
- All configuration is passed inline in the runtime request — there is no stored config object to resolve. Unlike `topic_relevance`, which looks up scope text from a persisted `TopicRelevanceConfig`, `llm_critic` receives `metrics`, `max_score`, and `llm_callable` directly in the guardrail request payload.

Recommendation:

- `input` or `output` depending on whether you are evaluating user input quality or model output quality.

Parameters / customization:

- `metrics: dict` (required) — metric name-to-description mapping passed to the LLM judge
- `max_score: int` (required) — maximum score per metric; used to define the scoring scale
- `llm_callable: str` (required) — model identifier passed to LiteLLM (e.g. `gpt-4o-mini`, `gpt-4o`)
- `on_fail`

Notes / limitations:

- All three parameters are required and must be provided inline in every runtime guardrail request; there is no stored config to reference.
- **Requires `OPENAI_API_KEY` to be set in environment variables.** If the key is not configured, `build()` raises a `ValueError` with an explicit message before any validation runs.
- Quality and latency depend on the chosen `llm_callable`.
- LLM-judge approaches can be inconsistent across runs; consider setting `max_score` conservatively and reviewing outputs before production use.

### 6) Topic Relevance Validator (`topic_relevance`)

Code:

- Config: `backend/app/core/validators/config/topic_relevance_safety_validator_config.py`
- Runtime validator: `backend/app/core/validators/topic_relevance.py`
- Prompt templates: `backend/app/core/validators/prompts/topic_relevance/`

What it does:

- Checks whether the user message is in scope using an LLM-critic style metric.
- Builds the final prompt from:
  - a versioned markdown template (`prompt_schema_version`)
  - tenant-specific `configuration` (string sub-prompt text).

Why this is used:

- Enforces domain scope for assistants that should answer only allowed topics.
- Keeps prompt wording versioned and reusable while allowing tenant-level scope customization.

Recommendation:

- primarily `input`
  - Why `input`: blocks out-of-scope prompts before model processing.
  - Add to `output` only when you also need to enforce output-topic strictness.

Parameters / customization:

- `topic_relevance_config_id: UUID` (required at runtime; resolves configuration and prompt version from tenant config)
- `prompt_schema_version: int` (optional; defaults to `1`)
- `llm_callable: str` (default: `gpt-4o-mini`) — the model identifier passed to Guardrails' LLMCritic to perform the scope evaluation. This must be a model string supported by LiteLLM (e.g. `gpt-4o-mini`, `gpt-4o`). It controls which LLM is used to score whether the input is within the allowed topic scope; changing it affects cost, latency, and scoring quality.
- `on_fail`

Notes / limitations:

- Runtime validation requires `topic_relevance_config_id`.
- **Requires `OPENAI_API_KEY` to be set in environment variables.** If the key is not configured, validation returns a `FailResult` with an explicit message.
- Configuration is resolved in `backend/app/api/routes/guardrails.py` from tenant Topic Relevance Config APIs.
- Prompt templates must include the `{{TOPIC_CONFIGURATION}}` placeholder.

### 7) LlamaGuard 7B Validator (`llamaguard_7b`)

Code:

- Config: `backend/app/core/validators/config/llamaguard_7b_safety_validator_config.py`
- Source: Guardrails Hub (`hub://guardrails/llamaguard_7b`)

What it does:

- Classifies text as "safe" or "unsafe" using the LlamaGuard-7B model via remote inference on the Guardrails Hub.
- Checks against a configurable set of safety policies covering violence/hate, sexual content, criminal planning, weapons, illegal drugs, and self-harm encouragement.

Why this is used:

- Provides a model-level safety classifier as a complement to rule-based validators.
- Allows policy-targeted filtering (e.g. only flag content violating specific categories).

Recommendation:

- `input` and `output`
  - Why `input`: catches unsafe user prompts before model processing.
  - Why `output`: validates generated content against the same safety policies.

Parameters / customization:

- `policies: list[str] | None` (default: all policies enabled)
  - Available policy constants: `O1` (violence/hate), `O2` (sexual content), `O3` (criminal planning), `O4` (guns/illegal weapons), `O5` (illegal drugs), `O6` (encourage self-harm)
- `on_fail`

Notes / limitations:

- Remote inference requires network access to the Guardrails Hub API.
- No programmatic fix is applied on failure — `on_fail=fix` will behave like `on_fail=exception`.
- LlamaGuard policy classification may produce false positives in news, clinical, or legal contexts.

### 9) NSFW Text Validator (`nsfw_text`)

Code:

- Config: `backend/app/core/validators/config/nsfw_text_safety_validator_config.py`
- Source: Guardrails Hub (`hub://guardrails/nsfw_text`)

What it does:

- Classifies text as NSFW (not safe for work) using a HuggingFace transformer model.
- Validates at the sentence level by default; fails if any sentence exceeds the configured threshold.

Why this is used:

- Catches sexually explicit or otherwise inappropriate content that may not be covered by profanity or slur lists.
- Model-based approach handles paraphrased or implicit NSFW content better than keyword matching.

Recommendation:

- `input` and `output`
  - Why `input`: prevents explicit user messages from being processed or logged.
  - Why `output`: prevents the model from returning NSFW content to end users.

Parameters / customization:

- `threshold: float` (default: `0.8`) — probability threshold above which text is classified as NSFW
- `validation_method: str` (default: `"sentence"`) — granularity of validation; `"sentence"` checks each sentence independently. `"full"` validates the entire text.
- `device: str | None` (default: `"cpu"`) — inference device (`"cpu"` or `"cuda"`)
- `model_name: str | None` (default: `"textdetox/xlmr-large-toxicity-classifier"`) — HuggingFace model identifier used for classification. Other acceptable value: `"michellejieli/NSFW_text_classifier"`

- `on_fail`

Notes / limitations:

- Model runs locally; first use will download the model weights unless pre-cached.
- Default model is English-focused; multilingual NSFW detection may require a different `model_name`.
- No programmatic fix is applied on failure — detected text is not auto-redacted.
- Inference on CPU can be slow for long inputs; consider batching or GPU deployment for production.

### 8) Profanity Free Validator (`profanity_free`)

Code:

- Config: `backend/app/core/validators/config/profanity_free_safety_validator_config.py`
- Source: Guardrails Hub (`hub://guardrails/profanity_free`)

What it does:

- Detects profanity in text using the `alt-profanity-check` library.
- Fails validation if any profanity is detected.

Why this is used:

- linear SVM model based profanity checker that is fast (100 predictions in 3.5 ms)
- Suitable as a first-pass filter before more computationally expensive validators.

Recommendation:

- `input` and `output`
  - Why `input`: catches profane user messages early.
  - Why `output`: prevents model-generated profanity from reaching users.

Parameters / customization:

- `on_fail`

Notes / limitations:

- Not as accurate as more sophisticated ML models like finetuned RoBERTa but better than lexical matching based solutions.
- No programmatic fix is applied — detected text is not auto-redacted.
- English-focused; cross-lingual profanity may not be detected.

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

- Input guardrails: `pii_remover`, `uli_slur_match`, `ban_list`, `topic_relevance` (when scope enforcement is needed), `profanity_free`, `llamaguard_7b`
- Output guardrails: `pii_remover`, `uli_slur_match`, `gender_assumption_bias`, `ban_list`, `profanity_free`, `llamaguard_7b`

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
- `backend/app/core/validators/config/topic_relevance_safety_validator_config.py`
- `backend/app/core/validators/config/llamaguard_7b_safety_validator_config.py`
- `backend/app/core/validators/config/nsfw_text_safety_validator_config.py`
- `backend/app/core/validators/config/profanity_free_safety_validator_config.py`
- `backend/app/schemas/guardrail_config.py`
- `backend/app/schemas/validator_config.py`
