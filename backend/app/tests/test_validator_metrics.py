import logging
import re
from pathlib import Path
logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)
import os
os.environ["GUARDRAILS_RUNNER"] = "sync"
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
request_id = "123e4567-e89b-12d3-a456-426614174000"

#--------------General Evaluation Utils ----------------#
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


import json
from datetime import datetime
from pathlib import Path

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

def test_input_guardrails_with_lexical_slur(integration_client):
    df = pd.read_csv(BASE_DIR / "datasets" / "lexical_slur_testing_dataset.csv")
    df['uli_slur_match'] = df['commentText'].apply(lambda x: get_slur_detector_guardrail_response(x, integration_client))
    df.to_csv(BASE_DIR / "datasets" / "lexical_slur_testing_dataset_output.csv", index=False)


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
        return "no_pii"
    else:
        return "pii"

def test_pii_detection_guardrail_response(integration_client):
    def to_binary(x):
        return 1 if x == "pii" else 0

    df = pd.read_csv(BASE_DIR / "datasets" / "pii_detection_testing_dataset.csv")
    df['pii_remover'] = df['source_text'].apply(lambda x: get_pii_remover_guardrail_response(x, integration_client))
    df.to_csv(BASE_DIR / "datasets" / "pii_detection_testing_dataset_output.csv", index=False)
    df["y_true"] = df["label"].apply(to_binary)
    df["y_pred"] = df["pii_remover"].apply(to_binary)

    compute_and_dump_metrics(
        df["y_true"],
        df["y_pred"],
        out_path=BASE_DIR / "datasets" / "pii_metrics.json",
        guardrail_name="pii_remover",
        dataset_name="pii_detection_testing_dataset.csv",
    )