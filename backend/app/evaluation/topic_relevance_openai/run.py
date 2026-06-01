from __future__ import annotations

from pathlib import Path

import pandas as pd
from guardrails.validators import FailResult

from app.core.validators.topic_relevance_openai import TopicRelevanceOpenAI
from app.evaluation.common.helper import (
    Profiler,
    build_evaluation_report,
    compute_binary_metrics,
    write_csv,
    write_json,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets" / "topic_relevance"
OUT_DIR = BASE_DIR / "outputs" / "topic_relevance_openai"

DEFAULT_CONFIG = {
    "llm_callable": "gpt-4o-mini",
    "prompt_schema_version": 3,
    "threshold": 2,
}

EVALUATIONS = [
    {
        "domain": "education",
        "dataset": "education-topic-relevance-dataset.csv",
        "topic_config": "education_topic_config.txt",
    },
    {
        "domain": "healthcare",
        "dataset": "healthcare-topic-relevance-dataset.csv",
        "topic_config": "healthcare_topic_config.txt",
    },
]


def run_evaluation(config: dict) -> None:
    """
    Run the topic relevance (OpenAI) evaluation for a single domain config.
    Loads dataset and topic config, runs each input through TopicRelevanceOpenAI,
    computes binary and per-category metrics, and writes CSV and JSON to outputs.
    """
    domain = config["domain"]

    dataset_path = DATASETS_DIR / config["dataset"]
    topic_config_path = DATASETS_DIR / config["topic_config"]
    topic_config = topic_config_path.read_text()

    print(f"\nRunning topic relevance (OpenAI) evaluation: {domain}")

    df = pd.read_csv(dataset_path)

    validator = TopicRelevanceOpenAI(
        topic_config=topic_config,
        prompt_schema_version=DEFAULT_CONFIG["prompt_schema_version"],
        llm_callable=DEFAULT_CONFIG["llm_callable"],
        threshold=DEFAULT_CONFIG["threshold"],
    )

    normalized_df = pd.DataFrame(
        {
            "input": df["input"].astype(str),
            "category": df["category"].astype(str),
            "in_scope": df["scope"].apply(lambda x: 1 if x == "IN_SCOPE" else 0),
        }
    )

    normalized_df["y_true"] = (1 - normalized_df["in_scope"]).astype(int)

    with Profiler() as p:
        results = normalized_df["input"].apply(
            lambda x: p.record(lambda t: validator.validate(t, metadata=None), x)
        )

    normalized_df["y_pred"] = results.apply(lambda r: int(isinstance(r, FailResult)))
    normalized_df["scope_score"] = results.apply(
        lambda r: r.metadata.get("scope_score")
        if getattr(r, "metadata", None)
        else None
    )
    normalized_df["error_message"] = results.apply(
        lambda r: r.error_message if isinstance(r, FailResult) else ""
    )

    metrics = compute_binary_metrics(normalized_df["y_true"], normalized_df["y_pred"])

    metrics["category_metrics"] = {
        str(cat): {
            "num_samples": int(len(g)),
            **compute_binary_metrics(g["y_true"], g["y_pred"]),
        }
        for cat, g in normalized_df.groupby("category", dropna=False)
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    write_csv(normalized_df, OUT_DIR / f"{domain}-predictions.csv")

    write_json(
        build_evaluation_report(
            guardrail="topic_relevance_openai",
            num_samples=len(normalized_df),
            profiler=p,
            dataset=str(dataset_path),
            llm_callable=DEFAULT_CONFIG["llm_callable"],
            prompt_schema_version=DEFAULT_CONFIG["prompt_schema_version"],
            threshold=DEFAULT_CONFIG["threshold"],
            metrics=metrics,
        ),
        OUT_DIR / f"{domain}-metrics.json",
    )

    print(f"Completed {domain} evaluation")


def main() -> None:
    """Iterate over all entries in EVALUATIONS and run each domain evaluation in sequence."""
    for config in EVALUATIONS:
        run_evaluation(config)


if __name__ == "__main__":
    main()
