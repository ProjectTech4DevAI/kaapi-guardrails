"""
Evaluate textdetox/xlmr-large-toxicity-classifier on existing predictions.csv files.

Reads each dataset's predictions.csv (for the text + ground-truth label),
runs the HuggingFace model, computes binary metrics, and prints + saves results
to hf_textdetox_metrics.json alongside each predictions.csv.

Usage:
    HF_TOKEN=<your_token> uv run backend/app/evaluation/toxicity/hf_textdetox_eval.py
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
from huggingface_hub import InferenceClient
from tqdm import tqdm

from app.evaluation.common.helper import (
    compute_binary_metrics,
    summarize_latency,
    write_json,
)

MODEL = "textdetox/xlmr-large-toxicity-classifier"
LABEL_MAP = {"toxic": 1, "neutral": 0}
PER_CALL_DELAY = 0.3  # seconds between calls

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs" / "toxicity"

DATASETS = [
    {
        "name": "hasoc",
        "text_col": "text",
        "label_col": "task1",
        "label_map": {"HOF": 1, "NOT": 0},
    },
    {
        "name": "sharechat",
        "text_col": "commentText",
        "label_col": "label",
        "label_map": None,  # already numeric
    },
]


def classify(client: InferenceClient, text: str) -> int | None:
    """Return 1 (toxic) or 0 (neutral), or None on error."""
    try:
        results = client.text_classification(text, model=MODEL)
        top = max(results, key=lambda x: x.score)
        return LABEL_MAP.get(top.label)
    except Exception as e:
        print(f"\n[warn] classification failed: {e}")
        return None


def evaluate_dataset(client: InferenceClient, dataset: dict) -> dict:
    name = dataset["name"]
    csv_path = OUT_DIR / name / "predictions.csv"

    print(f"\n=== {name} ===")
    df = pd.read_csv(csv_path)

    text_col = dataset["text_col"]
    label_col = dataset["label_col"]
    label_map = dataset["label_map"]

    y_true_raw = df[label_col]
    y_true_all = (
        y_true_raw.map(label_map).tolist()
        if label_map
        else y_true_raw.astype(int).tolist()
    )
    texts = df[text_col].astype(str).tolist()

    y_pred_all: list[int | None] = []
    latencies: list[float] = []

    for text in tqdm(texts, desc=name, unit="sample"):
        start = time.perf_counter()
        pred = classify(client, text)
        latencies.append((time.perf_counter() - start) * 1000)
        y_pred_all.append(pred)
        time.sleep(PER_CALL_DELAY)

    # Filter out samples where classification failed
    pairs = [
        (yt, yp, lat)
        for yt, yp, lat in zip(y_true_all, y_pred_all, latencies)
        if yp is not None
    ]
    num_skipped = len(y_true_all) - len(pairs)

    y_true = [p[0] for p in pairs]
    y_pred = [p[1] for p in pairs]
    valid_latencies = [p[2] for p in pairs]

    metrics = compute_binary_metrics(y_true, y_pred)

    result = {
        "dataset": name,
        "model": MODEL,
        "num_samples": len(texts),
        "num_evaluated": len(pairs),
        "num_skipped": num_skipped,
        **metrics,
        "latency_ms": summarize_latency(valid_latencies),
    }

    print(
        f"  evaluated={len(pairs)}  skipped={num_skipped}\n"
        f"  accuracy={metrics['accuracy']}  precision={metrics['precision']}"
        f"  recall={metrics['recall']}  f1={metrics['f1']}\n"
        f"  tp={metrics['true_positive']}  tn={metrics['true_negative']}"
        f"  fp={metrics['false_positive']}  fn={metrics['false_negative']}"
    )

    return result


def main() -> None:
    api_key = os.environ.get("HF_TOKEN", "")
    client = InferenceClient(provider="auto", api_key=api_key)

    all_results = {}
    for dataset in DATASETS:
        result = evaluate_dataset(client, dataset)
        all_results[dataset["name"]] = result
        out_path = OUT_DIR / dataset["name"] / "hf_textdetox_metrics.json"
        write_json(result, out_path)
        print(f"  Saved → {out_path}")

    print("\n=== Summary ===")
    for name, r in all_results.items():
        print(f"{name}: accuracy={r['accuracy']} f1={r['f1']}")


if __name__ == "__main__":
    main()
