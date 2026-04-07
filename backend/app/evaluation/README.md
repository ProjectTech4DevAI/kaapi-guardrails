# Evaluation Guide

This document covers how to run offline evaluations for each validator, what datasets are used, how to execute each script, and how to interpret the output metrics.

## Folder Structure

```
backend/app/evaluation/
├── ban_list/
│   └── run.py                             # Ban list evaluation script
├── common/
│   └── helper.py                          # Shared utilities (Profiler, metrics, I/O)
├── datasets/                              # Evaluation datasets (downloaded separately)
│   ├── ban_list_testing_dataset.csv
│   ├── gender_bias_assumption_dataset.csv
│   ├── lexical_slur_testing_dataset.csv
│   ├── multi_validator_whatsapp_dataset.csv
│   ├── pii_detection_testing_dataset.csv
│   ├── sharechat_toxic_dataset.csv
│   ├── topic_relevance/                   # Topic relevance datasets (downloaded separately)
│   │   ├── education-topic-relevance-dataset.csv
│   │   ├── education_topic_config.txt
│   │   ├── healthcare-topic-relevance-dataset.csv
│   │   └── healthcare_topic_config.txt
│   └── toxicity/                          # Toxicity evaluation datasets
│       ├── toxicity_test_hasoc.csv
│       └── toxicity_test_sharechat.csv
├── gender_assumption_bias/
│   └── run.py                             # Gender assumption bias evaluation script
├── lexical_slur/
│   └── run.py                             # Lexical slur evaluation script
├── multiple_validators/
│   ├── config.json                        # Multi-validator run configuration
│   └── run.py                             # End-to-end multi-validator evaluation script
├── outputs/                               # Generated outputs (created at runtime)
│   ├── ban_list/
│   ├── gender_assumption_bias/
│   ├── lexical_slur/
│   ├── multi_validator_whatsapp/
│   ├── multiple_validators/
│   ├── pii_remover/
│   ├── topic_relevance/
│   └── toxicity/
│       ├── hasoc/
│       └── sharechat/
├── pii/
│   ├── entity_metrics.py                  # Per-entity PII metrics computation
│   └── run.py                             # PII evaluation script
├── topic_relevance/
│   └── run.py                             # Topic relevance evaluation script
└── toxicity/                              # Toxicity evaluation scripts
```

## Prerequisites

All evaluation scripts must be run from the `backend/` directory with the virtual environment active. Ensure dependencies are installed:

```bash
uv sync
source .venv/bin/activate
```

### Install Guardrails Hub validators

If running for the first time, install the hub-sourced validators (ban list, llm critic, llamaguard 7b, profanity free) using:

```bash
GUARDRAILS_HUB_API_KEY=<your-key> bash scripts/install_guardrails_from_hub.sh
```

The script reads `backend/app/core/validators/validators.json` to determine which validators to install. Set `ENABLE_REMOTE_INFERENCING=true` if any validator requires remote inference (e.g. `llamaguard_7b`):

```bash
GUARDRAILS_HUB_API_KEY=<your-key> ENABLE_REMOTE_INFERENCING=true bash scripts/install_guardrails_from_hub.sh
```

If `GUARDRAILS_HUB_API_KEY` is not set, hub validator installs are skipped — only local validators will be available.

### Additional setup

For PII evaluation, also install the spaCy model:

```bash
python -m spacy download en_core_web_lg
```

Validators that use LLM-as-judge approach will require credentials for LLM providers. To use Open AI ensure that `OPENAI_API_KEY` is set in the `.env` file. Currently topic relevance validator uses it.


## Running All Evaluations

To run all individual validator evaluations in sequence (lexical slur, PII, gender assumption bias, ban list, topic relevance):

```bash
bash scripts/run_all_evaluations.sh
```

This runs each `run.py` using `uv run python` from the `backend/` directory.

## Individual Validator Evaluations

Each validator has a dedicated `run.py` that loads a dataset, runs the validator on each row, and writes results to `outputs/<validator-name>/`.

Run any individual evaluation from the `backend/` directory:

```bash
python3 app/evaluation/<validator_folder>/run.py
```

### Lexical Slur (`uli_slur_match`)

**Script:** `app/evaluation/lexical_slur/run.py`

**Dataset:** `datasets/lexical_slur_testing_dataset.csv`

Expected columns:

- `commentText` — text to validate
- `label` — ground truth (`1` = abusive, `0` = not abusive)

**What it does:** Runs each row through the `LexicalSlur` validator and records a binary prediction (`1` if `FailResult`, `0` otherwise). Computes binary classification metrics against the ground truth labels.

**Output:**

```
outputs/lexical_slur/predictions.csv
outputs/lexical_slur/metrics.json
```

**Run:**

```bash
python3 app/evaluation/lexical_slur/run.py
```

---

### PII Remover (`pii_remover`)

**Script:** `app/evaluation/pii/run.py`

**Dataset:** `datasets/pii_detection_testing_dataset.csv`

Expected columns:

- `source_text` — original text containing PII
- `target_text` — expected anonymized text with entity placeholders (e.g. `[PHONE_NUMBER]`, `[PERSON]`)

**What it does:** Runs each row through `PIIRemover._validate()`. If the result is a `FailResult`, the `fix_value` (anonymized text) is used; otherwise the original is kept. Entity-level precision/recall/F1 are computed by comparing placeholder labels in the predicted vs expected anonymized text.

**Output:**

```
outputs/pii_remover/predictions.csv
outputs/pii_remover/metrics.json
```

`metrics.json` includes per-entity metrics (e.g. `PHONE_NUMBER`, `PERSON`, `IN_AADHAAR`) as well as overall performance stats.

**Run:**

```bash
python3 app/evaluation/pii/run.py
```

---

### Gender Assumption Bias (`gender_assumption_bias`)

**Script:** `app/evaluation/gender_assumption_bias/run.py`

**Dataset:** `datasets/gender_bias_assumption_dataset.csv`

Expected columns:

- `biased input` — text containing gender-assumptive language (expected to fail)
- `neutral output` — neutral equivalent text (expected to pass)

**What it does:** Each row contributes two validation calls — once for the biased input (ground truth `1`) and once for the neutral output (ground truth `0`). Binary metrics are computed across both sets combined.

**Output:**

```
outputs/gender_assumption_bias/predictions.csv
outputs/gender_assumption_bias/metrics.json
```

**Run:**

```bash
python3 app/evaluation/gender_assumption_bias/run.py
```

---

### Ban List (`ban_list`)

**Script:** `app/evaluation/ban_list/run.py`

**Dataset:** `datasets/ban_list_testing_dataset.csv`

Expected columns:

- `source_text` — original text
- `target_text` — expected redacted text (used to compute exact match)
- `label` (optional) — explicit ground truth label; if absent, derived from whether `source_text` differs from `target_text`

**What it does:** Runs multiple named evaluation configs defined in `BAN_LIST_EVALUATIONS` inside the script (currently `maternal_healthcare` with `banned_words = ["sonography", "gender check"]`). For each config, the validator is instantiated with the given banned words and run across the dataset. Both binary classification metrics and exact match rate against `target_text` are computed.

Each named config produces separate output files:

```
outputs/ban_list/<name>-predictions.csv
outputs/ban_list/<name>-metrics.json
```

**Run:**

```bash
python3 app/evaluation/ban_list/run.py
```

---

### Topic Relevance (`topic_relevance`)

**Script:** `app/evaluation/topic_relevance/run.py`

**Datasets:** `datasets/topic_relevance/<domain>-topic-relevance-dataset.csv`

Expected columns:

- `input` — user message to evaluate
- `category` — topic category label for grouping metrics
- `scope` — `IN_SCOPE` or `OUT_SCOPE` (ground truth)

The script runs two domain evaluations: `education` and `healthcare`. Each domain requires:

- A dataset CSV
- A plain-text topic config file (the scope definition passed to the validator as the prompt)

**What it does:** Initializes `TopicRelevance` with the domain's topic config text and runs each input through it. `IN_SCOPE` maps to ground truth `0` (should pass), `OUT_SCOPE` maps to `1` (should fail). Computes overall binary metrics and per-category breakdowns.

**Output per domain:**

```
outputs/topic_relevance/<domain>-predictions.csv
outputs/topic_relevance/<domain>-metrics.json
```

The predictions CSV includes `scope_score` (the LLM-assigned score) and `error_message` for failed validations.

**Run:**

```bash
python3 app/evaluation/topic_relevance/run.py
```

> **Note:** Requires `OPENAI_API_KEY` to be set. Uses `gpt-4o-mini` by default (`DEFAULT_CONFIG` in the script).

---

## Multiple Validators Evaluation (End-to-End)

This evaluation runs multiple validators **together** against a dataset via the live guardrails API. Unlike the individual evaluations above, this is an **end-to-end integration test** — it hits the API rather than calling validators directly.

**Script:** `app/evaluation/multiple_validators/run.py`

**Config:** `app/evaluation/multiple_validators/config.json`

**Dataset:** `datasets/multi_validator_whatsapp_dataset.csv`

Expected columns:

- `ID` — row identifier
- `Text` — input text
- `Validators_present` — (informational) which validators are relevant for that row

### Configuration

Edit `backend/app/evaluation/multiple_validators/config.json` to control which validators run, their parameters, and the dataset/output paths:

```json
{
  "dataset_path": "datasets/multi_validator_whatsapp_dataset.csv",
  "out_path": "outputs/multi_validator_whatsapp/predictions.csv",
  "organization_id": 1,
  "project_id": 1,
  "validators": [
    { "type": "uli_slur_match", "severity": "all", "on_fail": "fix" },
    { "type": "pii_remover", "on_fail": "fix" },
    { "type": "ban_list", "banned_words": ["sonography"], "on_fail": "fix" }
  ]
}
```

For the full list of supported validators and their config parameters, refer to the [Validator Configuration Guide](../../core/validators/README.md).

### Setup

1. Ensure `GUARDRAILS_API_URL` is set in your `.env` file (see `.env.example`). Optionally set `GUARDRAILS_TIMEOUT_SECONDS` (default: `60`).
2. Ensure the API is running and accessible at the configured URL.

### Run

```bash
python3 app/evaluation/multiple_validators/run.py --auth_token <your-token>
```

The `--auth_token` argument is the plain-text bearer token (without the `Bearer ` prefix).

**Output:**

```
outputs/multi_validator_whatsapp/predictions.csv
```

The output CSV contains `ID`, `text`, `validators_present`, and `response` (the `safe_text` returned by the API).

> This script does not compute accuracy metrics — it records the API responses for manual review.

---

## Understanding Output Metrics

### Binary Classification Metrics (`metrics.json`)

Used by lexical slur, gender assumption bias, ban list, and topic relevance evaluations.

| Metric             | Description                                               |
| ------------------ | --------------------------------------------------------- |
| `true_positive`  | Validator correctly flagged a harmful/out-of-scope input  |
| `true_negative`  | Validator correctly passed a safe/in-scope input          |
| `false_positive` | Validator flagged a safe input (over-detection)           |
| `false_negative` | Validator missed a harmful input (under-detection)        |
| `accuracy`       | `(TP + TN) / total`                                     |
| `precision`      | `TP / (TP + FP)` — how often a flag is correct         |
| `recall`         | `TP / (TP + FN)` — how often harmful inputs are caught |
| `f1`             | Harmonic mean of precision and recall                     |

### PII Entity Metrics (`metrics.json`)

The PII evaluation computes per-entity metrics by comparing entity placeholder labels (e.g. `[PHONE_NUMBER]`) in the predicted output vs the expected target.

| Metric             | Description                                    |
| ------------------ | ---------------------------------------------- |
| `true_positive`  | Entity type correctly detected and redacted    |
| `false_positive` | Entity type redacted but not present in target |
| `false_negative` | Entity type present in target but not redacted |
| `precision`      | `TP / (TP + FP)` per entity type             |
| `recall`         | `TP / (TP + FN)` per entity type             |
| `f1`             | Harmonic mean per entity type                  |

### Topic Relevance Category Metrics

In addition to overall binary metrics, the topic relevance evaluation produces `category_metrics` — the same precision/recall/F1 broken down by the `category` column in the dataset. This reveals which topic categories the validator handles well or struggles with.

### Performance Metrics

All `metrics.json` files include a `performance` block:

```json
"performance": {
  "latency_ms": {
    "mean": 12.4,
    "p95": 18.1,
    "max": 34.7
  },
  "memory_mb": 5.2
}
```

| Metric              | Description                                                       |
| ------------------- | ----------------------------------------------------------------- |
| `latency_ms.mean` | Average per-sample validation time in milliseconds                |
| `latency_ms.p95`  | 95th-percentile latency — useful for tail-latency analysis       |
| `latency_ms.max`  | Worst-case latency across all samples                             |
| `memory_mb`       | Peak memory usage during the evaluation run (via `tracemalloc`) |

## Dataset Structure

Download all datasets from [Google Drive](https://drive.google.com/drive/u/0/folders/1Rd1LH-oEwCkU0pBDRrYYedExorwmXA89). The Drive contains one folder per validator. Download the CSV files and place them in `backend/app/evaluation/datasets/`.

Each evaluation script expects a specific filename — files must be named exactly as listed below:

| Validator              | Expected filename                                                                                                     |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Lexical Slur           | `lexical_slur_testing_dataset.csv`                                                                                  |
| PII Remover            | `pii_detection_testing_dataset.csv`                                                                                 |
| Gender Assumption Bias | `gender_bias_assumption_dataset.csv`                                                                                |
| Ban List               | `ban_list_testing_dataset.csv`                                                                                      |
| Multiple Validators    | `multi_validator_whatsapp_dataset.csv`                                                                              |
| Topic Relevance        | `topic_relevance/education-topic-relevance-dataset.csv`, `topic_relevance/healthcare-topic-relevance-dataset.csv` |

Topic relevance also requires plain-text topic config files alongside each dataset:

- `topic_relevance/education_topic_config.txt`
- `topic_relevance/healthcare_topic_config.txt`

These describe the allowed topic scope for each domain and are read at runtime to construct the validator prompt.