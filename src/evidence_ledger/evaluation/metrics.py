"""Claim-level metrics helpers."""

from __future__ import annotations

from collections import Counter
from typing import Iterable


def precision_recall_f1(y_true: Iterable[str], y_pred: Iterable[str], positive: str = "SUPPORTED"):
    yt = list(y_true)
    yp = list(y_pred)
    tp = sum(1 for t, p in zip(yt, yp) if t == positive and p == positive)
    fp = sum(1 for t, p in zip(yt, yp) if t != positive and p == positive)
    fn = sum(1 for t, p in zip(yt, yp) if t == positive and p != positive)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def false_positive_rate(y_true: Iterable[str], y_pred: Iterable[str], positive: str = "SUPPORTED") -> float:
    yt = list(y_true)
    yp = list(y_pred)
    negatives = [(t, p) for t, p in zip(yt, yp) if t != positive]
    if not negatives:
        return 0.0
    fp = sum(1 for t, p in negatives if p == positive)
    return fp / len(negatives)


def localization_accuracy(expected_pairs: list[set[tuple[str, str]]], predicted_pairs: list[set[tuple[str, str]]]) -> float:
    if not expected_pairs:
        return 0.0
    hits = 0
    for exp, pred in zip(expected_pairs, predicted_pairs):
        if not exp:
            hits += 1 if not pred else 0
        elif exp & pred:
            hits += 1
    return hits / len(expected_pairs)


def confusion(y_true: Iterable[str], y_pred: Iterable[str]) -> dict[str, int]:
    return dict(Counter(f"{t}->{p}" for t, p in zip(y_true, y_pred)))
