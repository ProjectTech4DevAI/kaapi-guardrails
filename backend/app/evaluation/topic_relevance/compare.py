"""
Compare OpenAI direct vs Guardrails TopicRelevance validator on the education dataset.

Both methods use the same prompt template (v1.md) and topic config (education_topic_config.txt).

Output columns added to the dataset:
  - scope_pred_openai       : IN_SCOPE | OUT_OF_SCOPE
  - scope_reason_openai     : brief reason from the LLM
  - scope_pred_guardrails   : IN_SCOPE | OUT_OF_SCOPE
  - scope_reason_guardrails : scope score returned by the LLMCritic

Usage (from backend/):
    python -m app.evaluation.topic_relevance.compare
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from guardrails.validators import FailResult, PassResult
from openai import OpenAI
from sklearn.metrics import classification_report, confusion_matrix
from tqdm import tqdm

from app.core.validators.topic_relevance import TopicRelevance

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets" / "topic_relevance"
OUT_DIR = BASE_DIR / "outputs" / "topic_relevance"
PROMPTS_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "core"
    / "validators"
    / "prompts"
    / "topic_relevance"
)

DATASET = "education-topic-relevance-dataset.csv"
TOPIC_CONFIG_FILE = "education_topic_config.txt"
MODEL = "gpt-4o-mini"
PROMPT_SCHEMA_VERSION = 1
PLACEHOLDER = "{{TOPIC_CONFIGURATION}}"
API_KEY = "<ADD-KEY>"

client = OpenAI(api_key=API_KEY)


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------


def _load_prompt_template() -> str:
    return (PROMPTS_DIR / f"v{PROMPT_SCHEMA_VERSION}.md").read_text(encoding="utf-8")


def _build_openai_prompt(topic_config: str, message: str) -> str:
    """Inject topic config into the v1 template, append the message, and ask for JSON."""
    template = _load_prompt_template().replace(PLACEHOLDER, topic_config.strip())
    return (
        template
        + f"\n\nMessage: {json.dumps(message)}"
        + '\n\nReturn ONLY valid JSON: {"score": <1|2|3>, "reason": "<one short sentence>"}'
    )


# ---------------------------------------------------------------------------
# OpenAI direct classification
# ---------------------------------------------------------------------------


def classify_openai(message: str, topic_config: str) -> tuple[str, str]:
    prompt = _build_openai_prompt(topic_config, message)

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        parsed = json.loads(response.choices[0].message.content)
        score = int(parsed["score"])
        reason = str(parsed.get("reason", ""))
    except Exception as exc:
        raise RuntimeError(
            f"Invalid LLM output: {response.choices[0].message.content}"
        ) from exc

    # Threshold matches LLMCritic config: score >= 2 → pass
    classification = "IN_SCOPE" if score >= 2 else "OUT_OF_SCOPE"
    return classification, reason


# ---------------------------------------------------------------------------
# Guardrails TopicRelevance classification
# ---------------------------------------------------------------------------


def classify_guardrails(message: str, validator: TopicRelevance) -> tuple[str, str]:
    result = validator.validate(message, metadata=None)
    score = (
        result.metadata.get("scope_violation") or result.metadata.get("scope_score")
        if getattr(result, "metadata", None)
        else None
    )

    if isinstance(result, PassResult):
        classification = "IN_SCOPE"
        reason = f"scope_score: {score}" if score is not None else "passed validation"
    else:
        classification = "OUT_OF_SCOPE"
        reason = f"scope_score: {score}" if score is not None else result.error_message

    return classification, reason


# ---------------------------------------------------------------------------
# Metrics display
# ---------------------------------------------------------------------------


def print_metrics(method_name: str, y_true: pd.Series, y_pred: pd.Series) -> None:
    labels = ["IN_SCOPE", "OUT_OF_SCOPE"]

    print(f"\n{'=' * 64}")
    print(f"  METHOD: {method_name}")
    print(f"{'=' * 64}")

    print("\nClassification Report:")
    print(classification_report(y_true, y_pred, labels=labels, zero_division=0))

    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_df = pd.DataFrame(
        cm,
        index=[f"True {l}" for l in labels],
        columns=[f"Pred {l}" for l in labels],
    )
    print("Confusion Matrix:")
    print(cm_df.to_string())
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    topic_config = (DATASETS_DIR / TOPIC_CONFIG_FILE).read_text(encoding="utf-8")
    df = pd.read_csv(DATASETS_DIR / DATASET)

    # --- OpenAI ---
    print("\nRunning OpenAI direct classification …")
    openai_results = []
    for msg in tqdm(df["input"].tolist(), desc="OpenAI"):
        openai_results.append(classify_openai(msg, topic_config))

    df["scope_pred_openai"] = [r[0] for r in openai_results]
    df["scope_reason_openai"] = [r[1] for r in openai_results]

    # --- Guardrails ---
    print("\nRunning Guardrails TopicRelevance classification …")
    validator = TopicRelevance(
        topic_config=topic_config,
        prompt_schema_version=PROMPT_SCHEMA_VERSION,
        llm_callable=MODEL,
    )

    guardrails_results = []
    for msg in tqdm(df["input"].tolist(), desc="Guardrails"):
        guardrails_results.append(classify_guardrails(msg, validator))

    df["scope_pred_guardrails"] = [r[0] for r in guardrails_results]
    df["scope_reason_guardrails"] = [r[1] for r in guardrails_results]

    # --- Metrics ---
    print_metrics("OpenAI Direct", df["scope"], df["scope_pred_openai"])
    print_metrics("Guardrails TopicRelevance", df["scope"], df["scope_pred_guardrails"])

    # --- Save ---
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUT_DIR / "education-comparison.csv"
    df.to_csv(output_path, index=False)
    print(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
