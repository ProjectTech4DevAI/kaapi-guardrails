from pathlib import Path
import pandas as pd
from guardrails.validators import FailResult

from app.core.validators.gender_assumption_bias import GenderAssumptionBias
from app.evaluation.common.helper import (
    compute_binary_metrics,
    Profiler,
    write_csv,
    write_json,
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs" / "gender_assumption_bias"

df = pd.read_csv(BASE_DIR / "datasets" / "gender_bias_assumption_dataset.csv")

validator = GenderAssumptionBias()

with Profiler() as p:
    df["biased_result"] = (
        df["biased input"]
        .astype(str)
        .apply(lambda x: p.record(lambda t: validator.validate(t, metadata=None), x))
    )

    df["neutral_result"] = (
        df["neutral output"]
        .astype(str)
        .apply(lambda x: p.record(lambda t: validator.validate(t, metadata=None), x))
    )

# For biased input → should FAIL (1)
df["biased_pred"] = df["biased_result"].apply(lambda r: int(isinstance(r, FailResult)))

# For neutral output → should PASS (0)
df["neutral_pred"] = df["neutral_result"].apply(
    lambda r: int(isinstance(r, FailResult))
)

df["biased_true"] = 1
df["neutral_true"] = 0

y_true = list(df["biased_true"]) + list(df["neutral_true"])
y_pred = list(df["biased_pred"]) + list(df["neutral_pred"])

metrics = compute_binary_metrics(y_true, y_pred)

write_csv(
    df.drop(columns=["biased_result", "neutral_result"]),
    OUT_DIR / "predictions.csv",
)

write_json(
    {
        "guardrail": "gender_assumption_bias",
        "num_samples": len(df) * 2,  # because evaluating both sides
        "metrics": metrics,
        "performance": {
            "latency_ms": {
                "mean": sum(p.latencies) / len(p.latencies),
                "p95": sorted(p.latencies)[int(len(p.latencies) * 0.95)],
                "max": max(p.latencies),
            },
            "memory_mb": p.peak_memory_mb,
        },
    },
    OUT_DIR / "metrics.json",
)
