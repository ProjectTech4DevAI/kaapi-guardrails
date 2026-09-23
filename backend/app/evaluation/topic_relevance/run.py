from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from guardrails.validators import FailResult

from app.core.config import settings
from app.core.validators.topic_relevance_llm import TopicRelevanceLLM
from app.evaluation.common.helper import (
    Profiler,
    build_evaluation_report,
    build_validator_config,
    combine_binary_metrics,
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


# v2 = forbidden-topics-only scoring (see prompts/topic_relevance_llm/v2.md);
# matches the education/healthcare configs, which now list forbidden topics only.
TOPIC_RELEVANCE_LLM_PROMPT_SCHEMA_VERSION = 2


def _build_topic_relevance(topic_config: str):
    # Imported lazily: TopicRelevance pulls in guardrails.hub's LLMCritic, which
    # requires the llm_critic hub validator to be installed. Deferring the import
    # means selecting only --backend topic_relevance_llm doesn't need that install.
    from app.core.validators.topic_relevance import TopicRelevance

    return TopicRelevance(
        topic_config=topic_config,
        prompt_schema_version=1,
        llm_callable=settings.DEFAULT_LLM_CALLABLE,
    )


BACKENDS = [
    {
        "name": "topic_relevance",
        "out_dir": OUTPUTS_DIR / "topic_relevance",
        "build": _build_topic_relevance,
        "config_fields": lambda v: {
            "llm_callable": v.llm_callable,
            "prompt_schema_version": v.prompt_schema_version,
        },
    },
    {
        "name": "topic_relevance_llm",
        "out_dir": OUTPUTS_DIR / "topic_relevance_llm",
        "build": lambda tc: TopicRelevanceLLM(
            system_prompt=tc,
            llm_callable=settings.DEFAULT_LLM_CALLABLE,
            threshold=settings.TOPIC_RELEVANCE_LLM_THRESHOLD,
            prompt_schema_version=TOPIC_RELEVANCE_LLM_PROMPT_SCHEMA_VERSION,
        ),
        # TopicRelevanceLLM doesn't store prompt_schema_version on the instance
        # (it's only used to pick the prompt template at construction time), so
        # it's recorded here from the constant rather than read off the validator.
        "config_fields": lambda v: {
            "llm_callable": v.llm_callable,
            "threshold": v.threshold,
            "prompt_schema_version": TOPIC_RELEVANCE_LLM_PROMPT_SCHEMA_VERSION,
        },
    },
]


def run_evaluation(dataset: dict, backend: dict) -> dict:
    domain = dataset["domain"]
    topic_config = (DATASETS_DIR / dataset["topic_config"]).read_text()
    dataset_path = DATASETS_DIR / dataset["dataset"]
    out_dir: Path = backend["out_dir"]

    print(f"\nRunning {backend['name']} evaluation: {domain}")

    df = pd.read_csv(dataset_path)
    validator = backend["build"](topic_config)
    config = build_validator_config(validator, **backend["config_fields"](validator))

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
            config=config,
            metrics=metrics,
        ),
        out_dir / f"{domain}-metrics.json",
    )

    print(f"Completed {backend['name']} {domain} evaluation")

    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--backend",
        choices=[backend["name"] for backend in BACKENDS],
        help="Only run this backend (default: run all backends)",
    )
    args = parser.parse_args()

    backends = BACKENDS
    if args.backend:
        backends = [b for b in BACKENDS if b["name"] == args.backend]

    for backend in backends:
        domain_metrics = []
        domain_labels = []
        for dataset in DATASETS:
            domain_metrics.append(run_evaluation(dataset, backend))
            domain_labels.append(dataset["domain"])

        combined = combine_binary_metrics(domain_metrics, labels=domain_labels)
        write_json(
            {
                "guardrail": backend["name"],
                "domains": domain_labels,
                "num_samples": sum(
                    m["true_positive"] + m["true_negative"] + m["false_positive"] + m["false_negative"]
                    for m in domain_metrics
                ),
                **combined,
            },
            backend["out_dir"] / "combined-metrics.json",
        )
        print(f"\nWrote combined metrics for {backend['name']} across {domain_labels}")


if __name__ == "__main__":
    main()
