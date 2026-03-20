import json
from pathlib import Path
import argparse
import os
from uuid import uuid4

import httpx
import pandas as pd

from app.evaluation.common.helper import write_csv
from app.load_env import load_environment

load_environment()

BASE_DIR = Path(__file__).resolve().parent.parent

API_URL = os.getenv("GUARDRAILS_API_URL")
if not API_URL:
    raise ValueError("GUARDRAILS_API_URL environment variable must be set.")
TIMEOUT_SECONDS = float(os.getenv("GUARDRAILS_TIMEOUT_SECONDS", "60"))


def load_config(config_path: Path) -> dict:
    with open(config_path) as f:
        return json.load(f)


def call_guardrails(
    text: str,
    validators_payload: list[dict],
    organization_id: int,
    project_id: int,
    auth_token: str,
) -> str:
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    payload = {
        "request_id": str(uuid4()),
        "organization_id": organization_id,
        "project_id": project_id,
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
        "--auth_token",
        required=True,
        help="Bearer token value (without the 'Bearer ' prefix).",
    )
    args = parser.parse_args()

    config = load_config(Path(__file__).resolve().parent / "config.json")

    dataset_path = BASE_DIR / config["dataset_path"]
    out_path = BASE_DIR / config["out_path"]
    organization_id = config["organization_id"]
    project_id = config["project_id"]
    validators_payload = config["validators"]

    if not validators_payload:
        raise ValueError("No validators defined in config.")

    df = pd.read_csv(dataset_path)

    rows = []
    for _, row in df.iterrows():
        source_text = str(row.get("Text", ""))
        safe_text = call_guardrails(
            source_text,
            validators_payload,
            organization_id,
            project_id,
            args.auth_token,
        )

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
    write_csv(out_df, out_path)


if __name__ == "__main__":
    main()
