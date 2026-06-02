from __future__ import annotations

from pathlib import Path

import pandas as pd
from guardrails.validators import FailResult

from app.core.config import settings
from app.core.validators.topic_relevance import TopicRelevance
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
OUTPUTS_DIR = BASE_DIR / "outputs"

DATASETS = [
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

BACKENDS = [
    {
        "name": "topic_relevance",
        "out_dir": OUTPUTS_DIR / "topic_relevance",
        "build": lambda tc: TopicRelevance(
            topic_config=tc,
            prompt_schema_version=1,
            llm_callable=settings.DEFAULT_LLM_CALLABLE,
        ),
        "report_extra": {
            "llm_callable": settings.DEFAULT_LLM_CALLABLE,
            "prompt_schema_version": 1,
        },
    },
    {
        "name": "topic_relevance_openai",
        "out_dir": OUTPUTS_DIR / "topic_relevance_openai",
        "build": lambda tc: TopicRelevanceOpenAI(
            system_prompt=tc,
            llm_callable=settings.DEFAULT_LLM_CALLABLE,
            threshold=2,
        ),
        "report_extra": {
            "llm_callable": settings.DEFAULT_LLM_CALLABLE,
            "threshold": 2,
        },
    },
]


def run_evaluation(dataset: dict, backend: dict) -> None:
    domain = dataset["domain"]
    topic_config = (DATASETS_DIR / dataset["topic_config"]).read_text()
    dataset_path = DATASETS_DIR / dataset["dataset"]
    out_dir: Path = backend["out_dir"]

    print(f"\nRunning {backend['name']} evaluation: {domain}")

    df = pd.read_csv(dataset_path)
    validator = backend["build"](topic_config)

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

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(normalized_df, out_dir / f"{domain}-predictions.csv")
    write_json(
        build_evaluation_report(
            guardrail=backend["name"],
            num_samples=len(normalized_df),
            profiler=p,
            dataset=str(dataset_path),
            **backend["report_extra"],
            metrics=metrics,
        ),
        out_dir / f"{domain}-metrics.json",
    )

    print(f"Completed {backend['name']} {domain} evaluation")


def main() -> None:
    for backend in BACKENDS:
        for dataset in DATASETS:
            run_evaluation(dataset, backend)


if __name__ == "__main__":
    main()
