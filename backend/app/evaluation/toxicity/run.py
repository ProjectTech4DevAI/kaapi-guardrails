import argparse
from pathlib import Path
import pandas as pd
from guardrails.validators import FailResult

from app.core.validators.lexical_slur import LexicalSlur
from app.evaluation.common.helper import (
    build_evaluation_report,
    build_validator_config,
    compute_binary_metrics,
    Profiler,
    write_csv,
    write_json,
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs" / "toxicity"

DATASET_PATH = BASE_DIR / "datasets" / "toxicity" / "toxicity_test_combined.csv"
# Standardized columns: text, label (0/1), language, dataset (source name).
SOURCE_NAMES = ["hasoc", "sharechat", "lexical"]


def _build_llamaguard_7b():
    # Imported lazily: llamaguard_7b is not yet migrated off guardrails.hub (see
    # backend/app/core/validators/README.md), and its local .guardrails/hub_registry.json
    # entry still points at the now-defunct guardrails_grhub_llamaguard_7b package, so a
    # top-level import would break every run of this script, not just ones selecting it.
    from guardrails.hub import (
        LlamaGuard7B,
    )  # noqa: not yet migrated, see backend README

    return LlamaGuard7B(on_fail="noop")


def _build_nsfw_text():
    # Imported lazily so selecting other validators via --validators doesn't require
    # the nsfw_text package (and its model download) to be usable.
    from guardrails_ai.nsfw_text import NSFWText

    return NSFWText(
        threshold=0.8,
        validation_method="sentence",
        device="cpu",
        model_name="textdetox/xlmr-large-toxicity-classifier",
        on_fail="noop",
        use_local=True,
    )


def _build_profanity_free():
    # Imported lazily so selecting other validators via --validators doesn't require
    # the profanity_free package to be usable.
    from guardrails_ai.profanity_free import ProfanityFree

    return ProfanityFree(on_fail="noop")


VALIDATORS = {
    "llamaguard_7b": {
        "build": _build_llamaguard_7b,
        "config_fields": lambda v: {},
    },
    "nsfw_text": {
        "build": _build_nsfw_text,
        "config_fields": lambda v: {
            "threshold": 0.8,
            "validation_method": "sentence",
            "device": "cpu",
            "model_name": "textdetox/xlmr-large-toxicity-classifier",
            "use_local": True,
        },
    },
    "profanity_free": {
        "build": _build_profanity_free,
        "config_fields": lambda v: {},
    },
    "lexical_slur": {
        "build": lambda: LexicalSlur(on_fail="noop"),
        "config_fields": lambda v: {
            "severity": v.severity,
            "languages": v.languages,
            "num_slurs_loaded": len(v.slur_list),
        },
    },
}


def _source_metrics(df: pd.DataFrame, pred_col: str) -> dict:
    return {
        str(source): compute_binary_metrics(group["y_true"], group[pred_col])
        for source, group in df.groupby("dataset", dropna=False)
    }


def run_evaluation(validators: dict, sources: list[str] | None):
    df = pd.read_csv(DATASET_PATH)
    df["y_true"] = df["label"].astype(int)

    if sources:
        df = df[df["dataset"].isin(sources)].reset_index(drop=True)

    missing_text = df["text"].isna()
    if missing_text.any():
        df = df[~missing_text].copy()

    all_metrics = {}

    for validator_name, spec in validators.items():
        print(f"Running {validator_name}...")
        validator = spec["build"]()
        config = build_validator_config(validator, **spec["config_fields"](validator))

        with Profiler() as p:
            df[f"{validator_name}_result"] = df["text"].apply(
                lambda x: p.record(lambda t: validator.validate(t, metadata={}), x)
            )

        df[f"{validator_name}_pred"] = df[f"{validator_name}_result"].apply(
            lambda r: int(isinstance(r, FailResult))
        )

        if validator_name == "llamaguard_7b":
            df["llamaguard_7b_latency_ms"] = p.latencies

        metrics = compute_binary_metrics(df["y_true"], df[f"{validator_name}_pred"])
        metrics["source_metrics"] = _source_metrics(df, f"{validator_name}_pred")
        all_metrics[validator_name] = build_evaluation_report(
            guardrail=validator_name,
            num_samples=len(df),
            profiler=p,
            config=config,
            metrics=metrics,
        )

        df = df.drop(columns=[f"{validator_name}_result"])

    validator_pred_cols = [f"{name}_pred" for name in validators]
    df["combined_pred"] = df[validator_pred_cols].max(axis=1)
    combined_metrics = compute_binary_metrics(df["y_true"], df["combined_pred"])
    combined_metrics["source_metrics"] = _source_metrics(df, "combined_pred")
    all_metrics["combined"] = {
        "guardrail": "combined",
        "validators": list(validators.keys()),
        "num_samples": len(df),
        "metrics": combined_metrics,
    }

    pred_cols = ["y_true"] + validator_pred_cols + ["combined_pred"]
    latency_cols = (
        ["llamaguard_7b_latency_ms"] if "llamaguard_7b_latency_ms" in df.columns else []
    )
    write_csv(
        df[["text", "dataset", "language", *pred_cols, *latency_cols]],
        OUT_DIR / "predictions.csv",
    )
    write_json(all_metrics, OUT_DIR / "metrics.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validators",
        nargs="+",
        choices=list(VALIDATORS.keys()),
        help="Only run these validators (default: run all validators)",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=SOURCE_NAMES,
        help="Only run rows from these original dataset sources (default: run all)",
    )
    args = parser.parse_args()

    selected_validators = (
        {name: VALIDATORS[name] for name in args.validators}
        if args.validators
        else VALIDATORS
    )

    run_evaluation(selected_validators, args.sources)

    print("Done. Results saved to", OUT_DIR)


if __name__ == "__main__":
    main()
