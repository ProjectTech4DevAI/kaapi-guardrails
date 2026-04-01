"""Compute metrics for all combinations of 2, 3, and 4 validators (OR logic).

OR logic: if ANY validator in the group flagged the text, result = toxic (1).
A row is skipped only when ALL validators in the group returned None.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import pandas as pd

from app.evaluation.common.helper import compute_binary_metrics, write_json

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs" / "toxicity"

VALIDATORS = ["llama_guard_7b", "nsfw_text", "profanity_free", "toxic_language"]

DATASETS = [
    {
        "name": "hasoc",
        "label_col": "task1",
        "label_map": {"HOF": 1, "NOT": 0},
    },
    {
        "name": "sharechat",
        "label_col": "label",
        "label_map": None,
    },
]


def encode_output(output: str) -> int | None:
    if not isinstance(output, str):
        return None
    return 0 if output.lower().strip() == "pass" else 1


def combine_or(row: pd.Series, encoded_cols: list[str]) -> int | None:
    """OR combination: 1 if any validator flagged, 0 if all passed, None if all unknown."""
    values = [row[col] for col in encoded_cols]
    if any(v == 1 for v in values):
        return 1
    if any(v == 0 for v in values):
        return 0
    return None


def combo_name(validators: tuple[str, ...]) -> str:
    return " + ".join(v.replace("_", " ") for v in validators)


def combo_col(validators: tuple[str, ...]) -> str:
    return "combo_" + "_AND_".join(validators)


def run(dataset_config: dict) -> None:
    name = dataset_config["name"]
    label_col = dataset_config["label_col"]
    label_map = dataset_config["label_map"]
    dataset_out_dir = OUT_DIR / name

    print(f"\n=== Combined metrics: {name} ===")
    df = pd.read_csv(dataset_out_dir / "predictions.csv")
    df["y_true"] = (
        df[label_col].map(label_map) if label_map else df[label_col].astype(int)
    )

    # Encode individual validator outputs
    encoded: dict[str, pd.Series] = {}
    for v in VALIDATORS:
        col = f"guardrails_ai_{v}_output"
        encoded[v] = df[col].apply(encode_output)

    # Build all combinations of size 2, 3, 4
    combinations: list[tuple[str, ...]] = []
    for size in (2, 3, 4):
        combinations.extend(itertools.combinations(VALIDATORS, size))

    # Add combined columns to df
    for combo in combinations:
        enc_cols = []
        for v in combo:
            col = f"encoded_{v}"
            if col not in df.columns:
                df[col] = encoded[v]
            enc_cols.append(col)
        df[combo_col(combo)] = df.apply(combine_or, axis=1, encoded_cols=enc_cols)

    # Compute metrics for each combination
    combo_metrics: dict[str, dict] = {}
    for combo in combinations:
        col = combo_col(combo)
        valid_mask = df[col].notna()
        y_true = df.loc[valid_mask, "y_true"].tolist()
        y_pred = df.loc[valid_mask, col].astype(int).tolist()

        metrics = {
            "validators": list(combo),
            "num_evaluated": int(valid_mask.sum()),
            "num_skipped": int((~valid_mask).sum()),
            **compute_binary_metrics(y_true, y_pred),
        }
        key = combo_col(combo)
        combo_metrics[key] = metrics

        m = metrics
        print(
            f"  [{len(combo)}] {combo_name(combo)}: TP={m['true_positive']}, FP={m['false_positive']}, F1={m['f1']}"
        )

    # Drop helper encoded_ columns before saving
    df_out = df.drop(
        columns=[c for c in df.columns if c.startswith("encoded_") or c == "y_true"]
    )
    df_out.to_csv(dataset_out_dir / "predictions_combined.csv", index=False)

    write_json(
        {"dataset": name, "num_samples": len(df), "combinations": combo_metrics},
        dataset_out_dir / "multiple_metrics.json",
    )
    print(f"  Written: {dataset_out_dir / 'multiple_metrics.json'}")
    print(f"  Written: {dataset_out_dir / 'predictions_combined.csv'}")


if __name__ == "__main__":
    for dataset_config in DATASETS:
        run(dataset_config)
