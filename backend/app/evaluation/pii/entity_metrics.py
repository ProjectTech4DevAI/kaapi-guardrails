import re
from collections import defaultdict
from typing import Iterable, Dict, Set

# Matches placeholders like [PHONE_NUMBER], <IN_PAN>, etc.
ENTITY_PATTERN = re.compile(r"[\[<]([A-Z0-9_]+)[\]>]")


def extract_entities(text: str) -> Set[str]:
    """
    Extract entity labels from a masked/anonymized string.

    Examples:
        "Call me at [PHONE_NUMBER]" -> {"PHONE_NUMBER"}
        "<IN_PAN> <PHONE_NUMBER>"  -> {"IN_PAN", "PHONE_NUMBER"}
    """
    if not isinstance(text, str):
        return set()
    return set(ENTITY_PATTERN.findall(text))


def compare_entities(gold: Set[str], pred: Set[str]):
    """
    Compare gold vs predicted entity sets.
    """
    tp = gold & pred  # correctly detected
    fn = gold - pred  # missed entities
    fp = pred - gold  # hallucinated entities
    return tp, fp, fn


def compute_entity_metrics(
    gold_texts: Iterable[str],
    pred_texts: Iterable[str],
) -> Dict[str, dict]:
    """
    Compute per-entity TP / FP / FN counts across the dataset.
    """
    stats = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    for gold_txt, pred_txt in zip(gold_texts, pred_texts, strict=True):
        gold_entities = extract_entities(gold_txt)
        pred_entities = extract_entities(pred_txt)

        tp, fp, fn = compare_entities(gold_entities, pred_entities)

        for e in tp:
            stats[e]["tp"] += 1
        for e in fp:
            stats[e]["fp"] += 1
        for e in fn:
            stats[e]["fn"] += 1

    return finalize_entity_metrics(stats)


def finalize_entity_metrics(stats: Dict[str, dict]) -> Dict[str, dict]:
    """
    Convert raw counts into precision / recall / F1 per entity.
    """
    report = {}

    for entity, s in stats.items():
        tp, fp, fn = s["tp"], s["fp"], s["fn"]

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )

        report[entity] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    return report
