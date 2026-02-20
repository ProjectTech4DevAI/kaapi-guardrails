from pathlib import Path
import pandas as pd
from guardrails.validators import FailResult

from app.core.validators.pii_remover import PIIRemover
from app.evaluation.pii.entity_metrics import compute_entity_metrics
from app.evaluation.common.helper import Profiler, write_csv, write_json

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs" / "pii_remover"

df = pd.read_csv(BASE_DIR / "datasets" / "pii_detection_testing_dataset.csv")

validator = PIIRemover()


def run_pii(text: str) -> str:
    result = validator._validate(text)
    if isinstance(result, FailResult):
        return result.fix_value
    return text


with Profiler() as p:
    df["anonymized"] = (
        df["source_text"].astype(str).apply(lambda x: p.record(run_pii, x))
    )

entity_report = compute_entity_metrics(
    df["target_text"],
    df["anonymized"],
)

# ---- Save outputs ----
write_csv(df, OUT_DIR / "predictions.csv")

write_json(
    {
        "guardrail": "pii_remover",
        "num_samples": len(df),
        "entity_metrics": entity_report,
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
