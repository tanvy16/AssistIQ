# Phase 1 — Baseline A vs Research Solution B

| Feature | Current implementation (Baseline A) | Intended / research implementation (B) | Missing in app | Experiment |
|---------|-------------------------------------|----------------------------------------|----------------|------------|
| 1. IT ticket / intent classification | Ordered keyword intent; manual ticket category on create | TF–IDF SVM/LR/RF (optional transformer later) for AssistIQ intents; separate ticket-category study if public labels used | Trained classifier not in prod chat path | Exp A — **ran** (synthetic intents) |
| 2. Ticket / workflow routing | `INTENT_ROUTE_MAP` after intent | Direct route classifier + oracle-intent bound; false-automation metric | Direct route model not in prod | Exp B — **ran** |
| 3. RAG solution retrieval | hash-v1 + Chroma cosine, k=3 | Compare BM25 + denser lexical/vector methods; optional rerank; answer quality rubric | BM25/dense/rerank not in prod; no human answer ratings | Exp C — **ran** (hash/BM25/TF–IDF); Exp D answer quality — **Not evaluated** |
| 4. End-to-end ITSM (FCR/productivity) | Rule IT/password + mock adapters | Scripted scenarios vs manual checklist; defined FCR/time metrics | Live user study; real install/IAM | Exp E — **SIMULATED** (not live productivity) |
