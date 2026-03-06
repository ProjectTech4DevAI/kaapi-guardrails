import argparse
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


parser = argparse.ArgumentParser()
parser.add_argument(
    "--words",
    required=True,
    help="Comma-separated banned words",
)

args = parser.parse_args()

BANNED_WORDS = [word.strip() for word in args.words.split(",") if word.strip()]

dataset = pd.read_csv(DATASET_PATH)

validator = BanList(
    banned_words=BANNED_WORDS,
)


def run_ban_list(text: str) -> tuple[str, int]:
    result = validator.validate(text, metadata=None)
    if isinstance(result, FailResult):
        return (result.fix_value or text), 1
    return text, 0


with Profiler() as p:
    results = (
        dataset["source_text"].astype(str).apply(lambda x: p.record(run_ban_list, x))
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
            dataset["redacted_text"].astype(str) == dataset["target_text"].astype(str)
        ).mean()
    metrics["exact_match"] = round(float(exact_match), 2)

write_csv(dataset, OUT_DIR / "predictions.csv")

write_json(
    build_evaluation_report(
        guardrail="ban_list",
        num_samples=len(dataset),
        profiler=p,
        banned_words=BANNED_WORDS,
        dataset=str(DATASET_PATH.name),
        metrics=metrics,
    ),
    OUT_DIR / "metrics.json",
)
