from pathlib import Path
import json

import pandas as pd
from guardrails.validators import FailResult

from app.core.validators.answer_relevance_custom_llm import AnswerRelevanceCustomLLM
from app.evaluation.common.helper import (
    build_evaluation_report,
    compute_binary_metrics,
    Profiler,
    write_csv,
    write_json,
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "outputs" / "answer_relevance"
DATASET_PATH = BASE_DIR / "datasets" / "SNEHA-answer-relevance-testing-dataset.csv"

LLM_CALLABLE = "gpt-4o-mini"


def run_evaluation():
    print(f"\nRunning answer relevance evaluation on SNEHA dataset")
    print(f"Dataset: {DATASET_PATH.name}")
    print(f"LLM: {LLM_CALLABLE}")

    df = pd.read_csv(DATASET_PATH)

    df = df[
        df["Response"].str.strip()
        != "Please rephrase the query without unsafe content. Input is outside the allowed topic scope."
    ].reset_index(drop=True)

    print(f"Samples after filtering: {len(df)}")

    validator = AnswerRelevanceCustomLLM(llm_callable=LLM_CALLABLE)

    def run_answer_relevance(query: str, response: str):
        input_json = json.dumps({"query": query, "answer": response})
        return validator._validate(input_json)

    with Profiler() as p:
        df["result"] = df.apply(
            lambda row: p.record(
                run_answer_relevance,
                str(row["Query"]),
                str(row["Response"]),
            ),
            axis=1,
        )

    df["y_pred"] = df["result"].apply(lambda r: int(isinstance(r, FailResult)))

    # Is Topic relevant=yes → response is relevant to query → PassResult → 0
    # Is Topic relevant=no  → response is not relevant → FailResult → 1
    df["y_true"] = df["Is Topic relevant"].apply(
        lambda x: 0 if str(x).strip().lower() == "yes" else 1
    )

    df["llm_verdict"] = df["result"].apply(
        lambda r: r.error_message if isinstance(r, FailResult) else "relevant"
    )

    metrics = compute_binary_metrics(df["y_true"], df["y_pred"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    write_csv(
        df[
            [
                "Query",
                "Response",
                "Is Topic relevant",
                "y_true",
                "y_pred",
                "llm_verdict",
            ]
        ],
        OUT_DIR / "sneha-predictions.csv",
    )

    write_json(
        build_evaluation_report(
            guardrail="answer_relevance_custom_llm",
            num_samples=len(df),
            profiler=p,
            dataset=str(DATASET_PATH.name),
            llm_callable=LLM_CALLABLE,
            metrics=metrics,
        ),
        OUT_DIR / "sneha-metrics.json",
    )

    print("Completed answer relevance evaluation")


def main():
    run_evaluation()


if __name__ == "__main__":
    main()
