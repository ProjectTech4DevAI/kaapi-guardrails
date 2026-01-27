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
