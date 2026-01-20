from datetime import datetime
from pathlib import Path

import json
import logging
logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)
import os
os.environ["GUARDRAILS_RUNNER"] = "sync"
import time
import tracemalloc

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
request_id = "123e4567-e89b-12d3-a456-426614174000"

#--------------General Evaluation Utils ----------------#
def percentile(values, p):
    values = sorted(values)
    k = int(len(values) * p)
    return values[min(k, len(values) - 1)]

def compute_metrics(y_true, y_pred):
    tp = sum((yt == 1 and yp == 1) for yt, yp in zip(y_true, y_pred))
    tn = sum((yt == 0 and yp == 0) for yt, yp in zip(y_true, y_pred))
    fp = sum((yt == 0 and yp == 1) for yt, yp in zip(y_true, y_pred))
    fn = sum((yt == 1 and yp == 0) for yt, yp in zip(y_true, y_pred))

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / (tp + tn + fp + fn)

    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
    }

def compute_and_dump_metrics(
    y_true,
    y_pred,
    *,
    out_path,
    guardrail_name,
    dataset_name=None,
):
    metrics = compute_metrics(y_true, y_pred)

    report = {
        "guardrail": guardrail_name,
        "dataset": dataset_name,
        "num_samples": len(y_true),
        "metrics": metrics,
        "generated_at": datetime.utcnow().isoformat(),
    }

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

#--------------Slur detector Evaluation Utils ----------------#
def get_slur_detector_guardrail_response(input_text: str, integration_client):
    response = integration_client.post(
        "/api/v1/guardrails/input/",
        json={
            "request_id": request_id,
            "input": input_text,
            "validators": [
                {
                    "type": "uli_slur_match",
                    "severity": "all",
                    "on_fail": "exception"
                }
            ],
        },
    )
    return response

# Because the detector relies uses lexical slur matching rather than contextual understanding, it flags every instance containing terms from its slur lexicon as a positive match. 
# This leads to zero true negatives and a consistent pattern of false positives. 
def test_input_guardrails_with_lexical_slur(integration_client):
    def parse_slur_response(response):
        body = response.json()
        if body["success"] is False:
            return "slur"
        else:
            return "no_slur"
        
    def slur_to_binary(x):
        return 1 if x == "slur" else 0

    df = pd.read_csv(BASE_DIR / "datasets" / "lexical_slur_testing_dataset.csv")

    latencies = []

    tracemalloc.start()

    def profiled_call(text):
        start = time.perf_counter()
        response = get_slur_detector_guardrail_response(text, integration_client)
        latencies.append((time.perf_counter() - start) * 1000)
        return parse_slur_response(response)

    # ---- Run guardrail (profiled) ----
    df["uli_slur_match"] = df["commentText"].apply(profiled_call)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_memory_mb = peak / (1024 * 1024)

    # ---- Save output dataset ----
    df.to_csv(
        BASE_DIR / "datasets" / "lexical_slur_testing_dataset_output.csv",
        index=False,
    )

    # ---- Accuracy metrics ----
    df["y_true"] = df["label"]
    df["y_pred"] = df["uli_slur_match"].apply(slur_to_binary)

    accuracy_metrics = compute_metrics(df["y_true"], df["y_pred"])

    # ---- Unified report ----
    report = {
        "guardrail": "uli_slur_match",
        "dataset": "lexical_slur_testing_dataset.csv",
        "num_samples": int(len(df)),
        "distribution": {
            "slur": int(df["y_true"].sum()),
            "no_slur": int(len(df) - df["y_true"].sum()),
        },
        "accuracy": accuracy_metrics,
        "performance": {
            "latency_ms": {
                "mean": sum(latencies) / len(latencies),
                "p95": percentile(latencies, 0.95),
                "max": max(latencies),
            },
            "memory_mb": {
                "peak": peak_memory_mb,
            },
        },
        "generated_at": datetime.utcnow().isoformat(),
    }

    # ---- Write single JSON ----
    out_path = BASE_DIR / "datasets" / "lexical_slur_evaluation_report.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)


# #--------------PII Removal Evaluation Utils ----------------#

def get_pii_remover_guardrail_response(input_text: str, integration_client):
    response = integration_client.post(
        "/api/v1/guardrails/input/",
        json={
            "request_id": request_id,
            "input": input_text,
            "validators": [
                {
                    "type": "pii_remover",
                    "on_fail": "exception"
                }
            ],
        },
    )
    body = response.json()

    if body["success"] == False:
        return "pii"
    else:
        return "no_pii"

def test_pii_detection_guardrail_response(integration_client):
    def to_binary(x):
        return 1 if x == "pii" else 0

    df = pd.read_csv(BASE_DIR / "datasets" / "pii_detection_testing_dataset.csv")

    latencies = []

    tracemalloc.start()

    def profiled_call(text):
        start = time.perf_counter()
        result = get_pii_remover_guardrail_response(text, integration_client)
        latencies.append((time.perf_counter() - start) * 1000)
        return result

    # ---- Run guardrail (profiled) ----
    df["pii_remover"] = df["source_text"].apply(profiled_call)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_memory_mb = peak / (1024 * 1024)

    # ---- Save output dataset ----
    df.to_csv(
        BASE_DIR / "datasets" / "pii_detection_testing_dataset_output.csv",
        index=False,
    )

    # ---- Accuracy metrics ----
    df["y_true"] = df["label"].apply(to_binary)
    df["y_pred"] = df["pii_remover"].apply(to_binary)

    accuracy_metrics = compute_metrics(df["y_true"], df["y_pred"])

    # ---- Unified report ----
    report = {
        "guardrail": "pii_remover",
        "dataset": "pii_detection_testing_dataset.csv",
        "num_samples": int(len(df)),
        "distribution": {
            "pii": int(df["y_true"].sum()),
            "no_pii": int(len(df) - df["y_true"].sum()),
        },
        "accuracy": accuracy_metrics,
        "performance": {
            "latency_ms": {
                "mean": sum(latencies) / len(latencies),
                "p95": percentile(latencies, 0.95),
                "max": max(latencies),
            },
            "memory_mb": {
                "peak": peak_memory_mb,
            },
        },
        "generated_at": datetime.utcnow().isoformat(),
    }

    # ---- Write single JSON ----
    out_path = BASE_DIR / "datasets" / "pii_evaluation_report.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)