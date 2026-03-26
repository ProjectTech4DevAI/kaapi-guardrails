from __future__ import annotations

import ssl
import time
from pathlib import Path

import nltk
import pandas as pd
from tqdm import tqdm
from guardrails import Guard, OnFailAction
from guardrails.hub import LlamaGuard7B, NSFWText, ProfanityFree, ToxicLanguage

from app.evaluation.common.helper import (
    compute_binary_metrics,
    summarize_latency,
    write_csv,
    write_json,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets" / "toxicity"
OUT_DIR = BASE_DIR / "outputs" / "toxicity"

# SSL fix required for NLTK downloads used by NSFWText
# Source: https://stackoverflow.com/a/68310484 (ishwardgret, CC BY-SA 4.0)
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

nltk.download("punkt_tab", quiet=True)

# --- Dataset configurations ---
DATASETS = [
    {
        "name": "hasoc",
        "file": "toxicity_test_hasoc.csv",
        "text_col": "text",
        "label_col": "task1",
        "label_map": {"HOF": 1, "NOT": 0},
    },
    {
        "name": "sharechat",
        "file": "toxicity_test_sharechat.csv",
        "text_col": "commentText",
        "label_col": "label",
        "label_map": None,  # already numeric: 1=toxic, 0=not
    },
]

# --- Validator configurations ---
# Use OnFailAction.NOOP so failed validations return a response instead of raising
VALIDATORS = [
    {
        "name": "llama_guard_7b",
        "guard": Guard().use(LlamaGuard7B, on_fail=OnFailAction.NOOP),
    },
    {
        "name": "nsfw_text",
        "guard": Guard().use(
            NSFWText,
            threshold=0.8,
            validation_method="sentence",
            on_fail=OnFailAction.NOOP,
        ),
    },
    {
        "name": "profanity_free",
        "guard": Guard().use(ProfanityFree, on_fail=OnFailAction.NOOP),
    },
    {
        "name": "toxic_language",
        "guard": Guard().use(
            ToxicLanguage,
            threshold=0.5,
            validation_method="sentence",
            on_fail=OnFailAction.NOOP,
        ),
    },
]

PER_CALL_DELAY = 0.5  # seconds between calls
BATCH_SIZE = 80  # calls before cooldown
COOLDOWN = 30  # seconds to sleep after each batch


def run_validator(
    guard: Guard, texts: pd.Series, validator_name: str
) -> tuple[list[str], list[float]]:
    """Run a guard validator over all texts with throttling. Returns (outputs, latencies_ms)."""
    outputs: list[str] = []
    latencies: list[float] = []

    for i, text in enumerate(tqdm(texts, desc=validator_name, unit="sample")):
        result = ""
        for attempt in range(3):
            try:
                start = time.perf_counter()
                resp = guard.validate(str(text))
                latencies.append((time.perf_counter() - start) * 1000)

                if resp.validation_passed:
                    result = "pass"
                else:
                    result = resp.validation_summaries[0].failure_reason
                break

            except Exception as e:
                if "429" in str(e):
                    wait = 30 * (attempt + 1)
                    print(f"\n[{validator_name}] 429 → sleeping {wait}s")
                    time.sleep(wait)
                    continue
                result = str(e)
                latencies.append(0.0)
                break

        outputs.append(result)
        time.sleep(PER_CALL_DELAY)

        if (i + 1) % BATCH_SIZE == 0:
            print(f"\n[{validator_name}] Cooling down quota window...")
            time.sleep(COOLDOWN)

    return outputs, latencies


def encode_output(output: str) -> int | None:
    """Convert validator string output to binary label: 1=toxic/fail, 0=pass, None=unknown."""
    if not isinstance(output, str):
        return None
    lowered = output.lower().strip()
    if lowered == "pass":
        return 0
    return 1


def run_dataset_evaluation(dataset_config: dict) -> None:
    name = dataset_config["name"]
    text_col = dataset_config["text_col"]
    label_col = dataset_config["label_col"]
    label_map = dataset_config["label_map"]

    print(f"\n=== Running toxicity evaluation: {name} ===")

    df = pd.read_csv(DATASETS_DIR / dataset_config["file"])
    df = df[[text_col, label_col]].copy()
    df[text_col] = df[text_col].astype(str)

    df["y_true"] = (
        df[label_col].map(label_map) if label_map else df[label_col].astype(int)
    )

    validator_metrics: dict[str, dict] = {}

    for v_config in VALIDATORS:
        v_name = v_config["name"]
        guard = v_config["guard"]
        col = f"guardrails_ai_{v_name}_output"

        print(f"\n  Running validator: {v_name}")
        outputs, latencies = run_validator(guard, df[text_col], v_name)

        df[col] = outputs
        encoded = df[col].apply(encode_output)

        valid_mask = encoded.notna()
        y_true = df.loc[valid_mask, "y_true"].tolist()
        y_pred = encoded[valid_mask].astype(int).tolist()

        validator_metrics[v_name] = {
            "num_evaluated": int(valid_mask.sum()),
            "num_skipped": int((~valid_mask).sum()),
            **compute_binary_metrics(y_true, y_pred),
            "latency_ms": summarize_latency(latencies),
        }

    dataset_out_dir = OUT_DIR / name
    write_csv(df.drop(columns=["y_true"]), dataset_out_dir / "predictions.csv")
    write_json(
        {
            "dataset": name,
            "num_samples": len(df),
            "validator_metrics": validator_metrics,
        },
        dataset_out_dir / "metrics.json",
    )

    print(f"\nCompleted {name} evaluation.")


def main() -> None:
    for dataset_config in DATASETS:
        run_dataset_evaluation(dataset_config)


if __name__ == "__main__":
    main()
