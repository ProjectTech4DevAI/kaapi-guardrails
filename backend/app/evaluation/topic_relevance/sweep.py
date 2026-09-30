"""Supplementary sweep: both topic-relevance backends x both domains x prompt v1/v2/v3.

The repo harness (app/evaluation/topic_relevance/run.py) pins prompt_schema_version=1.
The shipped topic configs are written in forbidden-topic style, which matches v2/v3,
so this sweep is needed to compare the two validators on a fair prompt.

Writes app/evaluation/outputs/topic_relevance_comparison/{matrix.json,predictions-*.csv}.
"""

from __future__ import annotations

import io
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path
from time import perf_counter

import pandas as pd
from guardrails.validators import FailResult

from app.core.config import settings
from app.core.constants import TOPIC_OUT_OF_SCOPE_ERROR
from app.core.validators.topic_relevance import TopicRelevance
from app.core.validators.topic_relevance_llm import TopicRelevanceLLM
from app.evaluation.common.helper import compute_binary_metrics, write_csv, write_json

BASE = Path("app/evaluation")
DATA = BASE / "datasets" / "topic_relevance"
OUT = BASE / "outputs" / "topic_relevance_comparison"

DOMAINS = ["education", "healthcare"]
VERSIONS = [1, 2, 3]
WORKERS = 8

BACKENDS = {
    "topic_relevance": lambda tc, v: TopicRelevance(
        topic_config=tc, prompt_schema_version=v, llm_callable=settings.DEFAULT_LLM_CALLABLE
    ),
    "topic_relevance_llm": lambda tc, v: TopicRelevanceLLM(
        system_prompt=tc,
        prompt_schema_version=v,
        llm_callable=settings.DEFAULT_LLM_CALLABLE,
        threshold=settings.TOPIC_RELEVANCE_LLM_THRESHOLD,
    ),
}


def run_cell(domain: str, backend_name: str, version: int) -> dict:
    tc = (DATA / f"{domain}_topic_config.txt").read_text()
    df = pd.read_csv(DATA / f"{domain}-topic-relevance-dataset.csv")
    validator = BACKENDS[backend_name](tc, version)

    rows = pd.DataFrame(
        {
            "input": df["input"].astype(str),
            "category": df["category"].astype(str),
            # OUT_OF_SCOPE is the positive class (validator should flag it).
            "y_true": (df["scope"].astype(str) != "IN_SCOPE").astype(int),
        }
    )

    def one(text: str):
        t0 = perf_counter()
        # LLMCritic prints its parsed evaluation to stdout on every call.
        with redirect_stdout(io.StringIO()):
            res = validator.validate(text, metadata=None)
        return res, (perf_counter() - t0) * 1000

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        out = list(ex.map(one, rows["input"].tolist()))

    results = [r for r, _ in out]
    latencies = [ms for _, ms in out]

    rows["y_pred"] = [int(isinstance(r, FailResult)) for r in results]
    rows["scope_score"] = [
        (r.metadata or {}).get("scope_score") if getattr(r, "metadata", None) else None
        for r in results
    ]
    rows["error_message"] = [
        r.error_message if isinstance(r, FailResult) else "" for r in results
    ]

    # An LLM/parse failure is not a scope decision; count them separately.
    infra_errors = sum(
        1
        for r in results
        if isinstance(r, FailResult) and r.error_message != TOPIC_OUT_OF_SCOPE_ERROR
    )

    metrics = compute_binary_metrics(rows["y_true"], rows["y_pred"])
    metrics["category_metrics"] = {
        str(cat): {"num_samples": int(len(g)), **compute_binary_metrics(g["y_true"], g["y_pred"])}
        for cat, g in rows.groupby("category", dropna=False)
    }

    slug = f"{domain}-{backend_name}-v{version}"
    write_csv(rows, OUT / f"predictions-{slug}.csv")

    srt = sorted(latencies)
    return {
        "domain": domain,
        "backend": backend_name,
        "prompt_schema_version": version,
        "num_samples": len(rows),
        "metrics": metrics,
        "scope_score_null_rate": round(rows["scope_score"].isna().mean(), 3),
        "non_scope_failures": infra_errors,
        "latency_ms": {
            "mean": round(sum(latencies) / len(latencies), 1),
            "p95": round(srt[min(len(srt) - 1, int(len(srt) * 0.95))], 1),
            "max": round(max(latencies), 1),
        },
    }


def main() -> None:
    cells = []
    for domain in DOMAINS:
        for backend in BACKENDS:
            for version in VERSIONS:
                print(f"running {domain}/{backend}/v{version} ...", flush=True)
                cells.append(run_cell(domain, backend, version))
                c = cells[-1]
                print(
                    f"  f1={c['metrics']['f1']} acc={c['metrics']['accuracy']} "
                    f"p={c['metrics']['precision']} r={c['metrics']['recall']} "
                    f"mean={c['latency_ms']['mean']}ms",
                    flush=True,
                )

    write_json(
        {
            "model": settings.DEFAULT_LLM_CALLABLE,
            "threshold_llm_variant": settings.TOPIC_RELEVANCE_LLM_THRESHOLD,
            "workers": WORKERS,
            "note": "positive class = OUT_OF_SCOPE; latency is wall-clock under concurrency",
            "cells": cells,
        },
        OUT / "matrix.json",
    )
    print(f"\nwrote {OUT / 'matrix.json'}")


if __name__ == "__main__":
    sys.exit(main())
