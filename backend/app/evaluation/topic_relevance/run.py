from __future__ import annotations

from pathlib import Path

import pandas as pd
from guardrails.validators import FailResult

from app.core.validators.topic_relevance import TopicRelevance
from app.evaluation.common.helper import (
    Profiler,
    build_evaluation_report,
    compute_binary_metrics,
    write_csv,
    write_json,
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs" / "topic_relevance"
DATASET_PATH = (
    BASE_DIR / "datasets" / "topic_relevance" / "education-topic-relevance-dataset.csv"
)
TOPIC_CONFIG_PATH = (
    BASE_DIR / "datasets" / "topic_relevance" / "education_topic_config.txt"
)
LLM_CALLABLE = "gpt-4o-mini"
PROMPT_SCHEMA_VERSION = 1

if not TOPIC_CONFIG_PATH.exists():
    raise FileNotFoundError(f"Topic config file not found at {TOPIC_CONFIG_PATH}")

TOPIC_CONFIG = TOPIC_CONFIG_PATH.read_text()


df = pd.read_csv(DATASET_PATH)

validator = TopicRelevance(
    topic_config=TOPIC_CONFIG,
    prompt_schema_version=PROMPT_SCHEMA_VERSION,
    llm_callable=LLM_CALLABLE,
)

normalized_df = pd.DataFrame(
    {
        "input": df["input"].astype(str),
        "category": df["category"].astype(str),
        "in_scope": df["scope"].apply(lambda x: 1 if x == "IN_SCOPE" else 0),
    }
)

# Positive class is "out of scope" (validator should fail for these inputs).
normalized_df["y_true"] = (1 - normalized_df["in_scope"]).astype(int)

with Profiler() as p:
    results = normalized_df["input"].apply(
        lambda x: p.record(lambda t: validator.validate(t, metadata=None), x)
    )

normalized_df["y_pred"] = results.apply(lambda r: int(isinstance(r, FailResult)))
normalized_df["scope_score"] = results.apply(
    lambda r: r.metadata.get("scope_score") if getattr(r, "metadata", None) else None
)
normalized_df["error_message"] = results.apply(
    lambda r: r.error_message if isinstance(r, FailResult) else ""
)

metrics = compute_binary_metrics(normalized_df["y_true"], normalized_df["y_pred"])
metrics["accuracy"] = round(
    float((normalized_df["y_true"] == normalized_df["y_pred"]).mean()), 2
)
metrics["category_metrics"] = {
    str(category): {
        "num_samples": int(len(group)),
        **compute_binary_metrics(group["y_true"], group["y_pred"]),
    }
    for category, group in normalized_df.groupby("category", dropna=False)
}

write_csv(normalized_df, OUT_DIR / "predictions.csv")

write_json(
    build_evaluation_report(
        guardrail="topic_relevance",
        num_samples=len(normalized_df),
        profiler=p,
        dataset=str(DATASET_PATH),
        llm_callable=LLM_CALLABLE,
        prompt_schema_version=PROMPT_SCHEMA_VERSION,
        metrics=metrics,
    ),
    OUT_DIR / "metrics.json",
)
