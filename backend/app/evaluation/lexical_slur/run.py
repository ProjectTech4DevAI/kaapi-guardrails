from pathlib import Path
import pandas as pd
from guardrails.validators import FailResult

from app.core.validators.lexical_slur import LexicalSlur
from app.evaluation.common.helper import (
    build_evaluation_report,
    Profiler,
    compute_binary_metrics,
    write_csv,
    write_json,
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs" / "lexical_slur"

df = pd.read_csv(BASE_DIR / "datasets" / "lexical_slur_testing_dataset.csv")

validator = LexicalSlur()

with Profiler() as p:
    df["result"] = (
        df["commentText"]
        .astype(str)
        .apply(lambda x: p.record(lambda t: validator.validate(t, metadata=None), x))
    )

df["y_pred"] = df["result"].apply(lambda r: int(isinstance(r, FailResult)))
df["y_true"] = df["label"]

metrics = compute_binary_metrics(df["y_true"], df["y_pred"])

# ---- Save outputs ----
write_csv(df.drop(columns=["result"]), OUT_DIR / "predictions.csv")

write_json(
    build_evaluation_report(
        guardrail="lexical_slur",
        num_samples=len(df),
        profiler=p,
        metrics=metrics,
    ),
    OUT_DIR / "metrics.json",
)
