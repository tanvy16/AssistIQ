"""Experiment A: intent classification — keyword vs TF-IDF SVM/LR/RF."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.baseline_a_logic import keyword_intent  # noqa: E402

SEED = 42
OUT = ROOT / "results" / "classification"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def eval_preds(y_true, y_pred, labels):
    acc = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0)
    p, r, f, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    per_class = {
        lab: {
            "precision": float(p[i]),
            "recall": float(r[i]),
            "f1": float(f[i]),
            "support": int(support[i]),
        }
        for i, lab in enumerate(labels)
    }
    cm = confusion_matrix(y_true, y_pred, labels=labels).tolist()
    return {
        "accuracy": float(acc),
        "macro_f1": float(macro_f1),
        "per_class": per_class,
        "confusion_matrix_labels": labels,
        "confusion_matrix": cm,
        "result_type": "MEASURED",
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    train = load_jsonl(ROOT / "datasets" / "intent" / "train.jsonl")
    val = load_jsonl(ROOT / "datasets" / "intent" / "val.jsonl")
    test = load_jsonl(ROOT / "datasets" / "intent" / "test.jsonl")

    # Use train+val for final fit after choosing defaults (no heavy tuning to keep reproducible)
    X_train = [r["text"] for r in train + val]
    y_train = [r["intent"] for r in train + val]
    X_test = [r["text"] for r in test]
    y_test = [r["intent"] for r in test]
    labels = sorted(set(y_train) | set(y_test))

    results = {}

    # Baseline A keyword
    kw_pred = [keyword_intent(x) for x in X_test]
    results["keyword_baseline_a"] = eval_preds(y_test, kw_pred, labels)
    results["keyword_baseline_a"]["n_test"] = len(y_test)

    models = {
        "tfidf_linear_svm": Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
                ("clf", LinearSVC(random_state=SEED)),
            ]
        ),
        "tfidf_logreg": Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
                (
                    "clf",
                    LogisticRegression(max_iter=2000, random_state=SEED),
                ),
            ]
        ),
        "tfidf_random_forest": Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
                (
                    "clf",
                    RandomForestClassifier(
                        n_estimators=200, random_state=SEED, n_jobs=-1
                    ),
                ),
            ]
        ),
    }

    predictions = {"text": X_test, "gold": y_test, "keyword_baseline_a": kw_pred}

    for name, pipe in models.items():
        pipe.fit(X_train, y_train)
        pred = pipe.predict(X_test).tolist()
        predictions[name] = pred
        results[name] = eval_preds(y_test, pred, labels)
        results[name]["n_test"] = len(y_test)
        results[name]["n_train"] = len(y_train)

    (OUT / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (OUT / "predictions.json").write_text(json.dumps(predictions, indent=2), encoding="utf-8")
    (OUT / "classification_report_keyword.txt").write_text(
        classification_report(y_test, kw_pred, digits=4), encoding="utf-8"
    )
    print(json.dumps({k: {"accuracy": v["accuracy"], "macro_f1": v["macro_f1"]} for k, v in results.items()}, indent=2))


if __name__ == "__main__":
    main()
