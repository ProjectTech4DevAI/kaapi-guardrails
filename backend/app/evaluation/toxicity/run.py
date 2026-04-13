from pathlib import Path
import pandas as pd
from guardrails.hub import LlamaGuard7B, NSFWText, ProfanityFree
from guardrails.validators import FailResult

from app.evaluation.common.helper import (
    build_evaluation_report,
    compute_binary_metrics,
    Profiler,
    write_csv,
    write_json,
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs" / "toxicity"

DATASETS = {
    "hasoc": {
        "path": BASE_DIR / "datasets" / "toxicity" / "toxicity_test_hasoc.csv",
        "text_col": "text",
        "label_col": "task1",
        "label_map": {"HOF": 1, "NOT": 0},
    },
    "sharechat": {
        "path": BASE_DIR / "datasets" / "toxicity" / "toxicity_test_sharechat.csv",
        "text_col": "commentText",
        "label_col": "label",
        "label_map": None,  # already binary int
    },
}

VALIDATORS = {
    "llamaguard_7b": lambda: LlamaGuard7B(on_fail="noop"),
    "nsfw_text": lambda: NSFWText(
        threshold=0.8,
        validation_method="sentence",
        device="cpu",
        model_name="textdetox/xlmr-large-toxicity-classifier",
        on_fail="noop",
    ),
    "profanity_free": lambda: ProfanityFree(on_fail="noop"),
}


def run_dataset(dataset_name: str, dataset_cfg: dict):
    df = pd.read_csv(dataset_cfg["path"])
    text_col = dataset_cfg["text_col"]
    label_col = dataset_cfg["label_col"]
    label_map = dataset_cfg["label_map"]

    if label_map is not None:
        df["y_true"] = df[label_col].map(label_map)
    else:
        df["y_true"] = df[label_col].astype(int)

    all_metrics = {}

    for validator_name, build_fn in VALIDATORS.items():
        print(f"  Running {validator_name} on {dataset_name}...")
        validator = build_fn()

        with Profiler() as p:
            df[f"{validator_name}_result"] = (
                df[text_col]
                .astype(str)
                .apply(
                    lambda x: p.record(lambda t: validator.validate(t, metadata={}), x)
                )
            )

        df[f"{validator_name}_pred"] = df[f"{validator_name}_result"].apply(
            lambda r: int(isinstance(r, FailResult))
        )

        metrics = compute_binary_metrics(df["y_true"], df[f"{validator_name}_pred"])
        all_metrics[validator_name] = build_evaluation_report(
            guardrail=validator_name,
            dataset=dataset_name,
            num_samples=len(df),
            profiler=p,
            metrics=metrics,
        )

        df = df.drop(columns=[f"{validator_name}_result"])

    pred_cols = ["y_true"] + [f"{v}_pred" for v in VALIDATORS]
    write_csv(
        df[[text_col, *pred_cols]],
        OUT_DIR / f"predictions_{dataset_name}.csv",
    )
    write_json(all_metrics, OUT_DIR / f"metrics_{dataset_name}.json")


for dataset_name, dataset_cfg in DATASETS.items():
    print(f"Evaluating dataset: {dataset_name}")
    run_dataset(dataset_name, dataset_cfg)

print("Done. Results saved to", OUT_DIR)
