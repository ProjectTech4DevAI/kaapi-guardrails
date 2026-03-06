from __future__ import annotations

import argparse
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
DATASETS_DIR = BASE_DIR / "datasets" / "topic_relevance"
OUT_DIR = BASE_DIR / "outputs" / "topic_relevance"

DEFAULT_CONFIG = {
    "llm_callable": "gpt-4o-mini",
    "prompt_schema_version": 1,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run topic relevance evaluation")
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="Dataset CSV filename (e.g., education-topic-relevance-dataset.csv)",
    )
    parser.add_argument(
        "--topic-config",
        type=str,
        required=True,
        help="Topic config TXT filename (e.g., education_topic_config.txt)",
    )
    parser.add_argument(
        "--domain",
        type=str,
        required=True,
        help="Domain name for output files (e.g., education, healthcare)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    dataset_path = DATASETS_DIR / args.dataset
    topic_config_path = DATASETS_DIR / args.topic_config
    topic_config = topic_config_path.read_text()

    df = pd.read_csv(dataset_path)

    validator = TopicRelevance(
        topic_config=topic_config,
        prompt_schema_version=DEFAULT_CONFIG["prompt_schema_version"],
        llm_callable=DEFAULT_CONFIG["llm_callable"],
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
    metrics["accuracy"] = round(
        float((normalized_df["y_true"] == normalized_df["y_pred"]).mean()), 2
    )
    metrics["category_metrics"] = {
        str(cat): {
            "num_samples": int(len(g)),
            **compute_binary_metrics(g["y_true"], g["y_pred"]),
        }
        for cat, g in normalized_df.groupby("category", dropna=False)
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(normalized_df, OUT_DIR / f"{args.domain}-predictions.csv")
    write_json(
        build_evaluation_report(
            guardrail="topic_relevance",
            num_samples=len(normalized_df),
            profiler=p,
            dataset=str(dataset_path),
            llm_callable=DEFAULT_CONFIG["llm_callable"],
            prompt_schema_version=DEFAULT_CONFIG["prompt_schema_version"],
            metrics=metrics,
        ),
        OUT_DIR / f"{args.domain}-metrics.json",
    )


if __name__ == "__main__":
    main()
