"""Standard open-domain QA metrics: normalized Exact Match and token F1,
following the widely-used SQuAD / TriviaQA normalization convention
(lowercase, strip punctuation and articles, collapse whitespace)."""

from __future__ import annotations

import re
import string
from collections import Counter


def normalize_answer(text: str) -> str:
    text = text.lower()
    text = "".join(ch for ch in text if ch not in string.punctuation)
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def exact_match(prediction: str, gold_answers: list[str]) -> float:
    norm_pred = normalize_answer(prediction)
    return float(any(norm_pred == normalize_answer(g) for g in gold_answers))


def _f1(prediction: str, gold: str) -> float:
    pred_tokens = normalize_answer(prediction).split()
    gold_tokens = normalize_answer(gold).split()
    if not pred_tokens or not gold_tokens:
        return float(pred_tokens == gold_tokens)
    common = Counter(pred_tokens) & Counter(gold_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = num_same / len(pred_tokens)
    recall = num_same / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def f1_score(prediction: str, gold_answers: list[str]) -> float:
    return max((_f1(prediction, g) for g in gold_answers), default=0.0)
