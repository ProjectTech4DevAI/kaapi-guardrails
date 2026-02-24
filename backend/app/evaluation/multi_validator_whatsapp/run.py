from pathlib import Path
import argparse
import os
from uuid import uuid4

import httpx
import pandas as pd

from app.evaluation.common.helper import write_csv

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "datasets" / "multi_validator_whatsapp_dataset.csv"
OUT_PATH = BASE_DIR / "outputs" / "multi_validator_whatsapp" / "predictions.csv"

API_URL = os.getenv("GUARDRAILS_API_URL", "http://localhost:8001/api/v1/guardrails/")
TIMEOUT_SECONDS = float(os.getenv("GUARDRAILS_TIMEOUT_SECONDS", "60"))

VALIDATOR_TEMPLATES = {
    "uli_slur_match": {
        "type": "uli_slur_match",
        "severity": "all",
        "on_fail": "fix",
    },
    "pii_remover": {
        "type": "pii_remover",
        "on_fail": "fix",
    },
    "ban_list": {
        "type": "ban_list",
        "banned_words": ["sonography"],
        "on_fail": "fix",
    },
}


def call_guardrails(text: str, validators_payload: list[dict], auth_token: str) -> str:
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    payload = {
        "request_id": str(uuid4()),
        "organization_id": 1,
        "project_id": 1,
        "input": text,
        "validators": validators_payload,
    }

    try:
        response = httpx.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
        safe_text = body.get("data", {}).get("safe_text")
        if safe_text is None:
            return ""
        return str(safe_text)
    except httpx.HTTPError as exc:
        return f"REQUEST_ERROR: {exc}"
    except ValueError as exc:
        return f"JSON_ERROR: {exc}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validators_payload",
        required=True,
        help="Comma-separated validators, e.g. uli_slur_match or uli_slur_match,pii_remover",
    )
    parser.add_argument(
        "--auth_token",
        required=True,
        help="Bearer token value (without the 'Bearer ' prefix).",
    )
    args = parser.parse_args()

    selected_validators = [
        value.strip() for value in args.validators_payload.split(",") if value.strip()
    ]
    unknown = [name for name in selected_validators if name not in VALIDATOR_TEMPLATES]
    if not selected_validators or unknown:
        raise ValueError(
            "Invalid validators_payload. Supported values: "
            f"{', '.join(VALIDATOR_TEMPLATES.keys())}"
        )

    validators_payload = [
        dict(VALIDATOR_TEMPLATES[name]) for name in selected_validators
    ]

    df = pd.read_csv(DATASET_PATH)

    # Keep output names exactly as requested.
    rows = []
    for _, row in df.iterrows():
        source_text = str(row.get("Text", ""))
        safe_text = call_guardrails(source_text, validators_payload, args.auth_token)

        rows.append(
            {
                "ID": row.get("ID"),
                "text": source_text,
                "validators_present": row.get("Validators_present", ""),
                "response": safe_text,
            }
        )

    out_df = pd.DataFrame(
        rows, columns=["ID", "text", "validators_present", "response"]
    )
    write_csv(out_df, OUT_PATH)


if __name__ == "__main__":
    main()
