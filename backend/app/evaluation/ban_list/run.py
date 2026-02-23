import os
from pathlib import Path

import pandas as pd
from guardrails.hub import BanList
from guardrails.validators import FailResult

from app.evaluation.common.helper import (
    Profiler,
    compute_binary_metrics,
    write_csv,
    write_json,
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs" / "ban_list"
DATASET_PATH = BASE_DIR / "datasets" / "ban_list_testing_dataset.csv"

# Provide comma-separated words via env var BAN_LIST_WORDS, e.g.:
# BAN_LIST_WORDS="badword,slur,profanity"
DEFAULT_BANNED_WORDS = ["badword"]
BANNED_WORDS = [
    word.strip()
    for word in os.getenv("BAN_LIST_WORDS", ",".join(DEFAULT_BANNED_WORDS)).split(",")
    if word.strip()
]

df = pd.read_csv(DATASET_PATH)

validator = BanList(
    banned_words=BANNED_WORDS,
)


def run_ban_list(text: str):
    result = validator.validate(text, metadata=None)
    if isinstance(result, FailResult):
        return result.fix_value, 1
    return text, 0


with Profiler() as p:
    outputs = df["source_text"].astype(str).apply(lambda x: p.record(run_ban_list, x))

df["redacted_text"] = outputs.apply(lambda x: x[0])
df["y_pred"] = outputs.apply(lambda x: x[1])

if "label" in df.columns:
    df["y_true"] = df["label"].astype(int)
else:
    df["y_true"] = (
        df["source_text"].astype(str) != df["target_text"].astype(str)
    ).astype(int)

metrics = compute_binary_metrics(df["y_true"], df["y_pred"])

if "target_text" in df.columns:
    exact_match = (
        df["redacted_text"].astype(str) == df["target_text"].astype(str)
    ).mean()
    metrics["exact_match"] = round(float(exact_match), 2)

write_csv(df, OUT_DIR / "predictions.csv")

write_json(
    {
        "guardrail": "ban_list",
        "num_samples": len(df),
        "banned_words": BANNED_WORDS,
        "dataset": str(DATASET_PATH.name),
        "metrics": metrics,
        "performance": {
            "latency_ms": {
                "mean": round(sum(p.latencies) / len(p.latencies), 2),
                "p95": round(sorted(p.latencies)[int(len(p.latencies) * 0.95)], 2),
                "max": round(max(p.latencies), 2),
            },
            "memory_mb": round(p.peak_memory_mb, 2),
        },
    },
    OUT_DIR / "metrics.json",
)
