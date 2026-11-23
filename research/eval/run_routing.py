"""Experiment B: routing accuracy and false-automation rate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, f1_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.baseline_a_logic import INTENT_ROUTE_MAP, keyword_intent, route_for_intent  # noqa: E402

SEED = 42
OUT = ROOT / "results" / "routing"
AUTO_ROUTES = {"start_it_request", "start_password_reset"}


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def false_automation_rate(y_true, y_pred) -> float:
    """Fraction of examples where pred is IT/password route but gold is not."""
    n = len(y_true)
    if n == 0:
        return 0.0
    bad = sum(
        1
        for t, p in zip(y_true, y_pred)
        if p in AUTO_ROUTES and t not in AUTO_ROUTES
    )
    return bad / n


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    train = load_jsonl(ROOT / "datasets" / "routing" / "train.jsonl")
    val = load_jsonl(ROOT / "datasets" / "routing" / "val.jsonl")
    test = load_jsonl(ROOT / "datasets" / "routing" / "test.jsonl")

    X_train = [r["text"] for r in train + val]
    y_train = [r["gold_route"] for r in train + val]
    X_test = [r["text"] for r in test]
    y_test = [r["gold_route"] for r in test]
    labels = sorted(set(y_train) | set(y_test))

    # Pipeline 1: keyword intent + map (Baseline A)
    intent_pred = [keyword_intent(x) for x in X_test]
    map_pred = [route_for_intent(i) for i in intent_pred]

    # Pipeline 2: direct route classifier
    pipe = Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("clf", LinearSVC(random_state=SEED)),
        ]
    )
    pipe.fit(X_train, y_train)
    direct_pred = pipe.predict(X_test).tolist()

    # Pipeline 3: oracle intent + map (uses gold intent labels)
    oracle_pred = [INTENT_ROUTE_MAP[r["intent"]] for r in test]

    def pack(name, pred):
        return {
            "method": name,
            "result_type": "MEASURED",
            "n_test": len(y_test),
            "route_accuracy": float(accuracy_score(y_test, pred)),
            "macro_f1": float(f1_score(y_test, pred, average="macro", labels=labels, zero_division=0)),
            "per_route_recall": {
                lab: float(
                    recall_score(
                        y_test,
                        pred,
                        labels=[lab],
                        average="macro",
                        zero_division=0,
                    )
                )
                for lab in labels
            },
            "false_automation_rate": float(false_automation_rate(y_test, pred)),
        }

    results = {
        "intent_plus_route_map": pack("intent_plus_route_map", map_pred),
        "direct_tfidf_svm_route": pack("direct_tfidf_svm_route", direct_pred),
        "oracle_intent_plus_map": pack("oracle_intent_plus_map", oracle_pred),
    }

    preds = {
        "text": X_test,
        "gold_route": y_test,
        "intent_plus_route_map": map_pred,
        "direct_tfidf_svm_route": direct_pred,
        "oracle_intent_plus_map": oracle_pred,
    }

    (OUT / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (OUT / "predictions.json").write_text(json.dumps(preds, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
