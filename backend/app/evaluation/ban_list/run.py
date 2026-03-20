from pathlib import Path

import pandas as pd
from guardrails.hub import BanList
from guardrails.validators import FailResult

from app.evaluation.common.helper import (
    build_evaluation_report,
    Profiler,
    compute_binary_metrics,
    write_csv,
    write_json,
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs" / "ban_list"
DATASET_PATH = BASE_DIR / "datasets" / "ban_list_testing_dataset.csv"

# Define ban list evaluations here
BAN_LIST_EVALUATIONS = [
    {
        "name": "maternal_healthcare",
        "banned_words": ["sonography", "gender check"],
    },
    # Future configs can be added here
    # {
    #     "name": "abuse_terms",
    #     "banned_words": ["slur1", "slur2"],
    # },
]


def run_evaluation(config: dict):
    """
    Run the ban list evaluation for a single config.
    Instantiates a BanList validator with the given banned words, runs each row through it,
    computes binary metrics and exact-match rate if target text is available,
    and writes prediction CSV and metrics JSON to the output directory.
    """
    name = config["name"]
    banned_words = config["banned_words"]

    print(f"\nRunning ban list evaluation: {name}")
    print(f"Banned words: {banned_words}")

    dataset = pd.read_csv(DATASET_PATH)

    validator = BanList(banned_words=banned_words)

    def run_ban_list(text: str) -> tuple[str, int]:
        """Validate a single text and return the (possibly redacted) text and a binary prediction label."""
        result = validator.validate(text, metadata=None)
        if isinstance(result, FailResult):
            return (result.fix_value or text), 1
        return text, 0

    with Profiler() as p:
        results = (
            dataset["source_text"]
            .astype(str)
            .apply(lambda x: p.record(run_ban_list, x))
        )

    dataset["redacted_text"] = results.apply(lambda x: x[0])
    dataset["y_pred"] = results.apply(lambda x: x[1])

    if "label" in dataset.columns:
        dataset["y_true"] = dataset["label"].astype(int)
    else:
        dataset["y_true"] = (
            dataset["source_text"].astype(str) != dataset["target_text"].astype(str)
        ).astype(int)

    metrics = compute_binary_metrics(dataset["y_true"], dataset["y_pred"])

    if "target_text" in dataset.columns:
        if dataset.empty:
            exact_match = 0.0
        else:
            exact_match = (
                dataset["redacted_text"].astype(str)
                == dataset["target_text"].astype(str)
            ).mean()
        metrics["exact_match"] = round(float(exact_match), 2)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    write_csv(dataset, OUT_DIR / f"{name}-predictions.csv")

    write_json(
        build_evaluation_report(
            guardrail="ban_list",
            num_samples=len(dataset),
            profiler=p,
            banned_words=banned_words,
            dataset=str(DATASET_PATH.name),
            metrics=metrics,
        ),
        OUT_DIR / f"{name}-metrics.json",
    )

    print(f"Completed {name} evaluation")


def main():
    """Iterate over all entries in BAN_LIST_EVALUATIONS and run each evaluation in sequence."""
    for config in BAN_LIST_EVALUATIONS:
        run_evaluation(config)


if __name__ == "__main__":
    main()
