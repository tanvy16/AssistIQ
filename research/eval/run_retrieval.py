"""Experiment C: hash-v1 vs BM25 vs TF-IDF cosine retrieval @ k=3."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.baseline_a_logic import hash_embed, normalize_text  # noqa: E402

OUT = ROOT / "results" / "retrieval"
K = 3


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def metrics_at_k(ranked_ids: list[str], relevant: set[str], k: int) -> dict:
    top = ranked_ids[:k]
    hits = [1 if cid in relevant else 0 for cid in top]
    hit = 1.0 if any(hits) else 0.0
    prec = sum(hits) / k
    recall = len(set(top) & relevant) / len(relevant) if relevant else 0.0
    mrr = 0.0
    for i, cid in enumerate(top, start=1):
        if cid in relevant:
            mrr = 1.0 / i
            break
    return {"hit": hit, "precision": prec, "recall": recall, "mrr": mrr}


def aggregate(per_query: list[dict]) -> dict:
    keys = ["hit", "precision", "recall", "mrr"]
    return {f"{key}_at_{K}" if key != "mrr" else "mrr": float(np.mean([p[key] for p in per_query])) for key in keys}


def rank_hash(query: str, chunks: list[dict]) -> list[str]:
    qv = hash_embed(query)
    scored = []
    for ch in chunks:
        # Chroma uses cosine distance; app uses s=max(0,1-d). For unit vectors, cosine sim ≈ 1-d/2...
        # Baseline A stores cosine *distance* from Chroma. For unit vectors, distance = 1 - cos_sim
        # (common Chroma convention). Match app: s = max(0, cos_sim) via s=max(0,1-d) with d=1-cos.
        sim = sum(a * b for a, b in zip(qv, hash_embed(ch["content"])))
        d = 1.0 - sim
        s = max(0.0, 1.0 - d)  # equals max(0, sim)
        scored.append((s, ch["chunk_id"]))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [cid for _, cid in scored]


def rank_bm25(query: str, chunks: list[dict], bm25: BM25Okapi, tokenized_corpus) -> list[str]:
    scores = bm25.get_scores(normalize_text(query).split())
    order = np.argsort(scores)[::-1]
    return [chunks[i]["chunk_id"] for i in order]


def rank_tfidf(query: str, chunks: list[dict], vectorizer: TfidfVectorizer, matrix) -> list[str]:
    qv = vectorizer.transform([query])
    sims = cosine_similarity(qv, matrix).ravel()
    order = np.argsort(sims)[::-1]
    return [chunks[i]["chunk_id"] for i in order]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    chunks = load_jsonl(ROOT / "datasets" / "kb" / "chunks.jsonl")
    queries = load_jsonl(ROOT / "datasets" / "qrels" / "queries.jsonl")
    qrels_rows = load_jsonl(ROOT / "datasets" / "qrels" / "qrels.jsonl")
    qrels = defaultdict(set)
    for row in qrels_rows:
        if row["relevance"] > 0:
            qrels[row["query_id"]].add(row["chunk_id"])

    tokenized = [normalize_text(c["content"]).split() for c in chunks]
    bm25 = BM25Okapi(tokenized)
    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform([c["content"] for c in chunks])

    methods = {
        "hash_v1_chroma_style": lambda q: rank_hash(q, chunks),
        "bm25": lambda q: rank_bm25(q, chunks, bm25, tokenized),
        "tfidf_cosine": lambda q: rank_tfidf(q, chunks, vectorizer, matrix),
    }

    all_results = {}
    all_preds = {}
    for name, rank_fn in methods.items():
        per = []
        preds = []
        by_stratum = defaultdict(list)
        for q in queries:
            ranked = rank_fn(q["text"])
            m = metrics_at_k(ranked, qrels[q["query_id"]], K)
            per.append(m)
            by_stratum[q["stratum"]].append(m)
            preds.append({"query_id": q["query_id"], "ranked": ranked[:K], "metrics": m})
        summary = aggregate(per)
        summary["result_type"] = "MEASURED"
        summary["n_queries"] = len(queries)
        summary["k"] = K
        summary["by_stratum"] = {s: aggregate(v) for s, v in by_stratum.items()}
        all_results[name] = summary
        all_preds[name] = preds

    (OUT / "metrics.json").write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    (OUT / "predictions.json").write_text(json.dumps(all_preds, indent=2), encoding="utf-8")
    print(json.dumps(all_results, indent=2))


if __name__ == "__main__":
    main()
