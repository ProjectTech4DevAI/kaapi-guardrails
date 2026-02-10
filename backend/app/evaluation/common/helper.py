from pathlib import Path
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


def compute_binary_metrics(y_true, y_pred):
    tp = sum((yt == 1 and yp == 1) for yt, yp in zip(y_true, y_pred, strict=True))
    tn = sum((yt == 0 and yp == 0) for yt, yp in zip(y_true, y_pred, strict=True))
    fp = sum((yt == 0 and yp == 1) for yt, yp in zip(y_true, y_pred, strict=True))
    fn = sum((yt == 1 and yp == 0) for yt, yp in zip(y_true, y_pred, strict=True))

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
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
