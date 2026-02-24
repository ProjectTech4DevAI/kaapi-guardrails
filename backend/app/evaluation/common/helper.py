from pathlib import Path
from typing import Any
import json
import pandas as pd
import time
import tracemalloc


def write_csv(df: pd.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_json(obj: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)


def summarize_latency(latencies: list[float]) -> dict[str, float]:
    if not latencies:
        return {"mean": 0.0, "p95": 0.0, "max": 0.0}

    sorted_latencies = sorted(latencies)
    p95_idx = min(len(sorted_latencies) - 1, int(len(sorted_latencies) * 0.95))

    return {
        "mean": round(sum(latencies) / len(latencies), 2),
        "p95": round(sorted_latencies[p95_idx], 2),
        "max": round(max(latencies), 2),
    }


def build_performance_payload(profiler: "Profiler") -> dict[str, Any]:
    return {
        "latency_ms": summarize_latency(profiler.latencies),
        "memory_mb": round(profiler.peak_memory_mb, 2),
    }


def build_evaluation_report(
    guardrail: str,
    num_samples: int,
    profiler: "Profiler",
    **extra_fields: Any,
) -> dict[str, Any]:
    return {
        "guardrail": guardrail,
        "num_samples": num_samples,
        **extra_fields,
        "performance": build_performance_payload(profiler),
    }


def compute_binary_metrics(y_true, y_pred):
    tp = sum((yt == 1 and yp == 1) for yt, yp in zip(y_true, y_pred, strict=True))
    tn = sum((yt == 0 and yp == 0) for yt, yp in zip(y_true, y_pred, strict=True))
    fp = sum((yt == 0 and yp == 1) for yt, yp in zip(y_true, y_pred, strict=True))
    fn = sum((yt == 1 and yp == 0) for yt, yp in zip(y_true, y_pred, strict=True))

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "precision": round(precision, 2),
        "recall": round(recall, 2),
        "f1": round(f1, 2),
    }


class Profiler:
    def __enter__(self):
        self.latencies = []
        tracemalloc.start()
        return self

    def record(self, fn, *args):
        start = time.perf_counter()
        result = fn(*args)
        self.latencies.append((time.perf_counter() - start) * 1000)
        return result

    def __exit__(self, *args):
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.peak_memory_mb = peak / (1024 * 1024)
