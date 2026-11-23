# AssistIQ — Literature-Driven Research Methodology Plan

**Status:** Audit and experimental plan for supervisor approval.  
**Constraint:** No application/Baseline A code changes. No evaluation pipeline implemented yet. No fabricated scores.  
**Date basis:** AssistIQ repository inspection + project literature matrix / review documents.  
**Citation note:** Literature percentages below are attributed to cited works as summarised in the project survey and spot-checked against public metadata (e.g. IEEE abstract for Dlodlo & Sibanda). Full-text metric definitions should be confirmed from PDFs before final paper submission. Figures are **not** AssistIQ results and are **not** cross-study comparable.

---

## A. Read-only implementation audit

### A.1 What exists today (Baseline A)

| Area | Actual implementation | ML? |
|------|----------------------|-----|
| Intent detection | Ordered keyword/substring match in `detect_intent.py`; optional LightweightML **hit-rate** remap only if keyword result is `knowledge_query` | No trained classifier |
| Ticket category | Manual `TicketCategory` on create (`network/access/hardware/software/other`); chat does **not** auto-classify tickets | No |
| Routing | `INTENT_ROUTE_MAP` dictionary → LangGraph node | No |
| Embeddings | `HashEmbeddingService` / `hash-v1`, dim 384, SHA-256 bag + L2 | No learned embedding |
| Retrieval | Chroma HNSW cosine; `k=3`; published filter; Postgres chunk join; \(s=\max(0,1-d)\) | ANN search, not trained IR |
| Confidence | Thresholds 0.65 / 0.35 on **top** similarity | Heuristic |
| RAG | Prompt with DATA framing; hist ≤6×400; KB ≤5×500; external LLM generate; citation scrub; confidence | LLM is external learned model |
| IT workflow | Entity extract + catalog match + `evaluate_policy` → DENY/ESCALATE/APPROVAL/ALLOW → **MockExecutionAdapter** | Rules + mock |
| Password workflow | Verify → risk → policy → confirm → **MockIAMAdapter**; TTL 30 min | Rules + mock |
| Orchestration | LangGraph `chat_graph.py` state machine | Workflow graph |
| Observability IR metrics | Explicitly `"Not evaluated"` | — |

### A.2 What does **not** exist (for research)

- No locked labelled intent/routing/qrels/scenario datasets in-repo  
- No offline evaluation harness for SVM/BM25/transformer comparisons  
- No sklearn / BM25 / sentence-transformers in `requirements.txt`  
- No human answer-quality ratings or user-study logs  
- No AssistIQ-measured FCR / retention / productivity  

### A.3 Implemented vs proposed research

| Literature theme | AssistIQ today | Proposed research evaluation |
|------------------|----------------|------------------------------|
| Ticket/intent classification | Keyword intent; manual ticket category | Exp A: keyword baseline vs TF-IDF SVM/LR/(RF); optional transformer |
| Automated routing | Intent + map | Exp B: route accuracy + false-automation |
| Ticket categorisation | Manual enum on create | Optional Exp A′ on ticket title/description → `TicketCategory` if labelled set exists |
| RAG IT support | hash-v1 + Chroma + LLM | Exp C + D: retrieval baselines + answer quality |
| Solution retrieval / rerank | Top-3 only; no reranker | Exp C: BM25 + optional embedder; rerank only if resources allow |
| Agentic ITSM | Policy + mock automation | Exp E: scripted tasks vs documented manual process (simulated execution) |

### A.4 Freeze (must not change for Baseline A measurements)

Keyword intent order/table; `INTENT_ROUTE_MAP`; hash-v1 / 384; chunk 800/120; Chroma cosine; \(k=3\); confidence 0.65/0.35; RAG prompt structure; IT/password policies; mock adapters; LangGraph topology; manual ticket categories on create.

---

## B. Literature-to-feature mapping

| Cited study (survey) | Method (literature) | Reported metric (literature) | Metric definition caution | AssistIQ component | How we use it in methodology |
|----------------------|---------------------|------------------------------|---------------------------|--------------------|------------------------------|
| Dlodlo & Sibanda, ZCICT 2023 (DOI 10.1109/ZCICT59466.2023.10528578) | Tuned SVM / KNN / RF for helpdesk tickets | **94.6% accuracy** (tuned SVM; undersampled data) | Accuracy on their balanced classes—not AssistIQ labels | Intent / future ticket category ML | Motivates Exp A baselines (TF-IDF + SVM etc.) |
| Feng et al., ZTE Comm. 2023 | BERT + clustering for dispatch routing | **86%** dispatch-department accuracy | Enterprise cloud tickets; department labels ≠ AssistIQ routes | Routing | Motivates Exp B; transformer only if feasible |
| Benitez Pereira et al., CYMAEN 2023 | Supervised ticket topic classifier + web app | **75% average precision** (7 categories) | Precision ≠ accuracy; 7 topics ≠ our 5–8 intents | Ticket categorisation / full-stack parity | Motivates category experiment + reporting AP |
| Schmidt et al., ICIS 2024 | DSR; RAG + vector DB for ITSM | **90.91%** preliminary “relevant documentation” ID accuracy | Preliminary MS KB test; not full answer quality | RAG retrieval | Motivates Exp C retrieval metrics |
| Cederlund et al., FMEC 2024 | LLM+RAG in live service desk | **38.4% solution retention** by technicians | Retention ≠ retrieval accuracy; Swedish desk | RAG answer quality | Motivates Exp D human/retention-style protocol |
| Kolagani, 2024 | Quasi-experiment agentic vs manual ITSM | Abstract **+53% FCR**, **+22% productivity**; body also reports FCR 60%→71% (conflict noted in project review) | Internal inconsistency; do not copy as AssistIQ target | IT/password workflows | Motivates Exp E task-completion vs manual process; **do not claim their %** |
| IBM / Packowski-style enterprise RAG (survey Paper 12) | Content quality + human-in-lead eval | Coverage / rewrite findings | Different corpus | KB + Exp D | Motivates groundedness/citation focus |

**Rule for the paper:** cite these as related work motivating *questions* and *baselines*. Never present them as AssistIQ measurements or as directly comparable leaderboard scores.

---

## C. Dataset suitability and label-mapping report

### C.1 Currently available operational data

KB documents/chunks + Chroma; tickets; IT/password records; chat messages/citations/telemetry; audit logs. **None are locked research qrels or intent gold labels.**

### C.2 Planned AssistIQ-native datasets (to construct)

| Dataset | Target size | Labels | Notes |
|---------|-------------|--------|-------|
| Intent (AssistIQ) | ≥300–500 utterances if feasible; ≥30–50/class where possible | `ChatIntent` (8 classes) | Primary for Exp A/B; 70/15/15 stratified; lock test |
| Routing | Same texts + gold `route` node | Map-compatible routes + false-automation cases | Exp B |
| Ticket category (optional) | ≥300 title+description | `TicketCategory` (5) | Only if separate from chat intent |
| RAG qrels | ≥100 queries if KB supports; ≥3 judgments/query | graded/binary relevance to chunk/doc ids | Exp C; strata: lexical vs paraphrase |
| Answer quality sample | 40–80 (Q, retrieved, answer) | rubric scores | Exp D |
| Workflow scenarios | ≥20–40 scripted tasks | success, escalate OK?, time, errors | Exp E; mock execution |

### C.3 Public IT/helpdesk datasets (candidates — verify licence before use)

| Candidate | Typical use | Suitability for AssistIQ | Mapping risk |
|-----------|-------------|--------------------------|--------------|
| Public ticket corpora used in prior ticket-classification papers (e.g. releases linked from Benitez Pereira et al. if available) | Category classification | Possible for **ticket category** Exp A′ | Labels rarely match AssistIQ `ChatIntent` |
| Generic IT incident / helpdesk Kaggle/GitHub dumps | Classification demos | Secondary / sensitivity analysis only | High mismatch; document unmappable classes |
| AssistIQ published KB (local) | Retrieval | **Required** for Exp C validity | N/A — native |

**Do not force-map** public ticket “network/hardware” categories onto chat intents such as `password_reset_request` or `human_escalation`. If a public set is used, run it as a **separate** ticket-category experiment with its original labels, and report AssistIQ chat-intent results only on AssistIQ-annotated data.

### C.4 Annotation guide (summary)

- One primary intent per utterance; mark `multi_intent=true` when two goals appear; primary = first actionable goal.  
- Escalation: explicit human/agent language → `human_escalation`.  
- Ambiguous “can’t log in” → annotate as password vs access with written rule (prefer password if reset language; else access/software).  
- Routing gold = intended LangGraph node after policy (e.g. privileged IT → still `start_it_request` but expect escalate outcome in Exp E).  
- Retrieval: independent judges; resolve disagreements by third adjudicator.  
- Keep train/val/test disjoint; hash near-duplicates out of test.

---

## D. Research question and hypothesis matrix

| ID | Research question | Working hypothesis (to be tested, not assumed true) | Experiment |
|----|-------------------|-----------------------------------------------------|------------|
| RQ1 | How accurate is Baseline A keyword intent vs classical TF-IDF classifiers on AssistIQ-labelled utterances? | Keyword rules work for exact phrases; TF-IDF SVM/LR improve paraphrase strata | A |
| RQ2 | Does correct intent+map routing achieve acceptable route accuracy, and where does false automation occur? | Most route errors are intent errors; false automation concentrates on soft access language | B |
| RQ3 | How does hash-v1+Chroma@3 compare to BM25 (and optional dense retrieval) on AssistIQ qrels? | Hash-v1 competitive on high lexical overlap; BM25/dense better on paraphrase/low-overlap | C |
| RQ4 | Do better retrieval rankings translate into better rated RAG answers? | Not necessarily; answer quality must be measured separately | D |
| RQ5 | For defined support tasks, how do AssistIQ policy workflows (mock) compare to a documented manual process on completion, time, and escalation appropriateness? | Policy automation reduces steps for low-risk catalog items; high-risk correctly escalates | E |

---

## E. Complete experimental plan

### Experiment A — Ticket / intent classification

- **Baseline:** AssistIQ `_keyword_intent` (and optional LightweightML path as ablation).  
- **Comparators (eval-only code, not production freeze):** TF-IDF + Linear SVM; TF-IDF + Logistic Regression; RF if justified; transformer classifier only if data/compute allow.  
- **Data:** AssistIQ intent set; optional separate ticket-category set.  
- **Split:** stratified 70/15/15; tune on val; report once on locked test.  
- **Metrics:** accuracy, macro-F1, per-class P/R, confusion matrix; paraphrase stratum accuracy.  
- **Seeds / versions:** record sklearn, random_state, Python, hardware.

### Experiment B — Workflow routing

- **Baseline:** keyword intent → `INTENT_ROUTE_MAP`.  
- **Comparator:** direct multi-class classifier predicting route node (same features as A); optional “oracle intent + map” upper bound.  
- **Metrics:** route accuracy; per-route F1; joint intent–route accuracy; **false-automation rate** = fraction wrongly sent to `start_it_request` or `start_password_reset` when gold is escalate/unsupported/knowledge.  
- Same eligible test utterances as A where labelled for both.

### Experiment C — Knowledge retrieval

- **Baseline:** hash-v1 + Chroma cosine @ \(k=3\), published only.  
- **Comparators:** BM25 over same chunk corpus; optional pretrained embedding index; optional cross-encoder rerank of top-\(N\) **only if** RQ justifies and resources exist.  
- **Data:** AssistIQ qrels; fixed test queries; no test tuning.  
- **Metrics:** Recall@3, MRR; optional Hit@3, Precision@3; stratify lexical vs paraphrase.

### Experiment D — RAG answer quality

- **Setup:** fix generator config (model id/version); vary retriever from Exp C or hold retrieval fixed.  
- **Rubric (define before rating):** correctness, relevance, groundedness, citation correctness (0–2 or 1–5 scale); latency wall-clock.  
- **Judges:** human primary; if LLM-as-judge used, name model/version, calibrate on ≥20 double-rated items, report agreement.  
- **Do not** equate \(s_{\mathrm{top}}\) with answer quality.

### Experiment E — Agentic / policy ITSM evaluation

- **Tasks:** small fixed set (install low-risk catalog item; medium-risk needing approval; privileged → escalate; password self-reset verify+confirm; password fail path).  
- **Conditions:** AssistIQ automated path vs documented **manual** checklist (same success criteria).  
- **Metrics:** task completion, time, error count, escalation appropriateness, brief user/operator feedback.  
- **Disclosure:** MockExecutionAdapter / MockIAMAdapter — **no** real install or live password change.

### Reporting tables (empty until measured)

Separate tables: classification | routing | retrieval | answer quality | workflow. Cells without runs = **Not evaluated**.

---

## F. Proposed evaluation-only directory structure and commands

Proposed **new** tree (not created until approved; must not alter Baseline A app modules):

```
research/
  datasets/
    intent/          # jsonl train/val/test
    routing/
    qrels/
    answer_quality/
    scenarios/
  annotation/
    guides/
  eval/
    classify_intent.py
    evaluate_routing.py
    evaluate_retrieval.py
    evaluate_rag_answers.py
    evaluate_workflows.py
  results/           # csv/json only after runs
  configs/
    baseline_a.yaml  # frozen params reference
  README.md
```

**Illustrative commands (after approval and deps installed in a separate venv):**

```powershell
cd research
python -m eval.classify_intent --config configs/baseline_a.yaml --split test
python -m eval.evaluate_routing --split test
python -m eval.evaluate_retrieval --method hash_v1 --k 3
python -m eval.evaluate_retrieval --method bm25 --k 3
python -m eval.evaluate_rag_answers --ratings path/to/ratings.jsonl
python -m eval.evaluate_workflows --scenarios datasets/scenarios/
```

Application Baseline A remains callable as a **black-box** baseline (e.g. import keyword intent / search_published) without changing frozen algorithms.

---

## G. Methodology draft (Sections 3.1–3.7)

### 3.1 Research design

This study evaluates a **hybrid AI and deterministic-policy ITSM framework**. AssistIQ combines intent identification, workflow routing, knowledge retrieval, retrieval-augmented response generation, and policy-controlled IT actions. Empirically, the frozen Baseline A pipeline is measured against established classification and retrieval methods drawn from the IT helpdesk literature, with separate assessment of answer quality and workflow outcomes. Literature-reported accuracies and ITSM gains motivate the experimental questions; they are not treated as AssistIQ performance.

### 3.2 Baseline system

Baseline A is the current AssistIQ implementation: ordered keyword intent detection; deterministic `INTENT_ROUTE_MAP` routing; hash-v1 embeddings (dimension 384); Chroma cosine HNSW retrieval with \(k=3\) and published-only filtering; similarity \(s_i=\max(0,1-d_i)\); confidence labels from the top score using thresholds 0.65 and 0.35; RAG prompting that marks retrieved text as DATA; generation via an external registry LLM; IT and password paths governed by deterministic policies terminating in mock adapters. Chat ticket-creation intent retrieves ticket context and does not insert tickets. These components remain frozen for baseline measurement.

### 3.3 Datasets and annotation

Primary evaluation uses AssistIQ-constructed labelled sets for intent, routing, retrieval qrels, answer-quality samples, and workflow scenarios (Section C). Public ticket corpora, if used, support a separate ticket-category experiment with native labels and explicit mapping limitations. Annotation follows a written guide covering multi-intent cases, escalation language, and retrieval judgment rules. Splits are stratified and locked; leakage controls are applied.

### 3.4 Comparative methods

Classification comparisons use TF-IDF with linear SVM and logistic regression (and RF or a transformer only if justified by data and resources). Routing comparisons use the intent-plus-map pipeline against a direct route classifier and an oracle-intent upper bound. Retrieval comparisons use BM25 and, if feasible, a pretrained dense retriever, with optional reranking as a secondary analysis. RAG answer evaluation holds or varies the retriever under a fixed generator configuration. Workflow evaluation contrasts AssistIQ policy automation with a documented manual process on the same tasks.

### 3.5 Experimental procedure

For each experiment, identical eligible test instances are used across methods. Hyperparameters are selected on validation data only. Random seeds, library versions, model identifiers, and hardware are logged. Confidence intervals or bootstrap uncertainty are reported where sample size allows. Failures to run a method are marked Not evaluated with a reason.

### 3.6 Evaluation metrics

Intent: accuracy, macro-F1, per-class precision/recall, confusion matrix. Routing: route accuracy, per-route scores, false-automation rate. Retrieval: Recall@3, MRR, optional Hit@3 and Precision@3. Answers: rubric scores for correctness, relevance, groundedness, citation correctness, plus latency. Workflows: completion, time, errors, escalation appropriateness, feedback. FCR, productivity, and retention are used only if AssistIQ-specific operational definitions are fixed in advance; Kolagani’s percentages are not adopted as targets.

### 3.7 Reproducibility

Baseline A parameters are version-pinned in a research config file. Evaluation code lives under a separate `research/` tree. Dataset versions are hashed. Commands to regenerate tables are documented. Application production code is not modified to “win” benchmarks.

---

## H. Outline for Results and Discussion

### Results (populate only after runs)

1. **Classification table** — keyword vs SVM vs LR (vs RF/transformer if run); paraphrase stratum.  
2. **Routing table** — map pipeline vs direct classifier; false-automation.  
3. **Retrieval table** — hash-v1 vs BM25 (vs dense/rerank if run); strata.  
4. **Answer quality table** — rubric means; latency; link to retrieval condition.  
5. **Workflow table** — AssistIQ vs manual checklist; escalate appropriateness; mock disclosure.

Every empty cell: **Not evaluated**.

### Discussion prompts (evidence-gated)

- Where keyword intent fails relative to TF-IDF SVM (paraphrase, multi-intent).  
- Whether routing errors are mostly intent errors.  
- Whether hash-v1’s lexical bias matches Exp C strata.  
- Whether Exp D shows retrieval gains without answer gains.  
- How policy gates behave vs manual process under mock constraints.  
- Explicit non-claims: no adoption of 94.6% / 86% / 38.4% / +53% FCR as AssistIQ results; no claim of live IAM/install.

---

## Framing sentence (refined)

> This study evaluates a hybrid IT helpdesk framework that combines rule-based intent identification, deterministic workflow routing, hash-based vector retrieval, retrieval-augmented response generation, and policy-controlled ITSM actions. Baseline AssistIQ performance is measured on AssistIQ-labelled tasks and compared with established classification and retrieval approaches from the IT support literature, with separate evaluation of answer quality and simulated workflow outcomes.

---

## Approval gate

**Before any evaluation pipeline is implemented, confirm:**

1. Approve Experiments A–E scope (including optional transformer / rerank / ticket-category A′).  
2. Approve AssistIQ-native annotation effort sizes.  
3. Approve whether public ticket data is in-scope as a **separate** category experiment.  
4. Approve creation of `research/` eval tree and extra Python dependencies in a **separate** environment (not changing Baseline A app requirements unless agreed).

Until approval: **no** sklearn/BM25 integration into the app, **no** Baseline A algorithm changes, **no** fabricated results, **no** GitHub push of eval work.

---

*End of plan. Application source code was not modified.*
