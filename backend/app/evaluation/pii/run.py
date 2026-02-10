from pathlib import Path
import pandas as pd
from guardrails.validators import FailResult

from app.core.validators.pii_remover import PIIRemover
from app.evaluation.pii.entity_metrics import compute_entity_metrics
from app.evaluation.common.helper import write_csv, write_json

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs" / "pii_remover"

df = pd.read_csv(BASE_DIR / "datasets" / "pii_detection_testing_dataset.csv")

validator = PIIRemover()


def run_pii(text: str) -> str:
    result = validator._validate(text)
    if isinstance(result, FailResult):
        return result.fix_value
    return text


df["anonymized"] = df["source_text"].astype(str).apply(run_pii)

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
    },
    OUT_DIR / "metrics.json",
)
