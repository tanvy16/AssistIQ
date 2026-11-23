# Solution / Methodology / Mathematical Implementation

**Scope note.** Baseline A denotes algorithms in the AssistIQ application. Research Solution B denotes evaluation implementations under `research/` that test intended completed-system methods. Results labelled **MEASURED** used locked synthetic AssistIQ-shaped datasets. Workflow timings are **SIMULATED**. Literature figures are not AssistIQ results. Generated-answer human ratings and live productivity studies are **Not evaluated**.

## 1. Proposed hybrid solution and technical implementation

AssistIQ is designed as a hybrid IT helpdesk framework: deterministic intent identification and routing select a workflow; hash-based vector retrieval and an external LLM support knowledge answers; rule-based policy engines govern software/access and password-reset actions (mock adapters in the current build). The frozen application baseline (Baseline A) provides the production reference. Comparative classifiers, BM25/TF–IDF retrieval, and a workflow simulator were implemented only under `research/` so experiments do not alter Baseline A code.

## 2. Four research features and algorithms

**Feature 1 — Intent / ticket classification.** Baseline A assigns intent by ordered keyword substring matching. Research Solution B compares that detector with TF–IDF + Linear SVM, TF–IDF + logistic regression, and TF–IDF + random forest on the same held-out utterances.

**Feature 2 — Workflow routing.** Baseline A maps intent \(c\) by \(r(c)=\texttt{INTENT\_ROUTE\_MAP}[c]\). Research Solution B evaluates (i) keyword intent + map, (ii) a direct TF–IDF SVM route classifier, and (iii) oracle-intent + map to separate routing from classification error. Chat ticket-creation intent routes to ticket-context retrieval and does not insert tickets.

**Feature 3 — RAG retrieval.** Baseline A embeds text with hash-v1 (\(d=384\)), retrieves top-\(k=3\) neighbours under cosine distance \(d_i\), and scores \(s_i=\max(0,1-d_i)\). Research Solution B compares hash-v1, BM25, and TF–IDF cosine on a fixed synthetic knowledge corpus with labelled qrels. Confidence uses \(s_{\mathrm{top}}\) with thresholds 0.65 / 0.35 (heuristic, not a probability). Dense sentence-transformer retrieval and human answer-quality rating remain Not evaluated in this run.

**Feature 4 — End-to-end ITSM effectiveness.** Baseline A encodes IT and password policies with mock execution/IAM. Research Solution B runs six scripted scenarios through the same policy rules and compares simulated step/time costs with a documented manual checklist. Outcomes are SIMULATED, not live wall-clock productivity.

## 3. Mathematical formulations and evaluation metrics

**Intent (Baseline A).** With lowercased text \(\ell(x)\) and keyword sets \(K_I\) in fixed order \(O\),
\[
I^{*}(x)=\min_{\prec}\{I\in O:\exists\,w\in K_I,\; w\subseteq \ell(x)\},
\]
else `GENERAL_QUERY` if “?” appears, else `KNOWLEDGE_QUERY`.

**Hash embedding.** For SHA-256 byte \(b\) at index \(i\), dimension \(d=384\):
\[
j=(b+i)\bmod d,\quad v_j\leftarrow v_j+1+\tfrac{b}{255},\quad e=v/\|v\|_2.
\]

**Retrieval metrics** (\(k=3\)). For relevant set \(R\) and ranked list \(L\),
\[
\mathrm{Recall@}k=\frac{|L_{1:k}\cap R|}{|R|},\quad
\mathrm{MRR}=\frac{1}{|Q|}\sum_{q}\frac{1}{\mathrm{rank}_q},\quad
\mathrm{Hit@}k=\mathbf{1}[L_{1:k}\cap R\neq\emptyset].
\]

**Classification.** Accuracy; macro-F1; per-class precision/recall.

**Routing.** Route accuracy; macro-F1; false-automation rate = fraction of cases where predicted route \(\in\{\texttt{start\_it\_request},\texttt{start\_password\_reset}\}\) but gold does not.

**Workflow (simulated).** Task completion = correct policy decisions / \(N\); simulated FCR = correct and not `ESCALATE` / \(N\); escalation appropriateness = agreement on escalate vs not.

## 4. Experimental setup

Synthetic AssistIQ-shaped intent/routing data (\(n=339\); train/val/test 237/51/51; seed 42) and a 10-chunk KB with 30 labelled queries (lexical vs paraphrase strata) were generated under `research/datasets/` and marked synthetic. Classification and routing models used scikit-learn; BM25 used `rank_bm25`. Workflow evaluation used six deterministic scenarios. No production application files were modified.

**Hypotheses (pre-result):** H1 keyword ≠ TF–IDF classifiers; H2 map pipeline ≠ direct route classifier; H3 BM25/TF–IDF ≠ hash-v1 on Recall@3/MRR; H4 simulation yields measurable completion/timing vs manual checklist (simulated only).

## 5. Compact results and interpretation

**Table 1. Intent classification (MEASURED, synthetic test \(n=51\)).**

| Method | Accuracy | Macro-F1 | Type |
|--------|----------|----------|------|
| Keyword Baseline A | 0.765 | 0.688 | MEASURED |
| TF–IDF Linear SVM | 0.922 | 0.886 | MEASURED |
| TF–IDF Logistic Regression | 0.902 | 0.817 | MEASURED |
| TF–IDF Random Forest | 0.961 | 0.939 | MEASURED |

**Table 2. Routing (MEASURED, synthetic test \(n=51\)).**

| Method | Route Acc. | Macro-F1 | False-automation | Type |
|--------|------------|----------|------------------|------|
| Intent + route map (A) | 0.784 | 0.662 | 0.000 | MEASURED |
| Direct TF–IDF SVM | 0.922 | 0.874 | 0.000 | MEASURED |
| Oracle intent + map | 1.000 | 1.000 | 0.000 | MEASURED |

**Table 3. Retrieval @ \(k=3\) (MEASURED, \(n=30\) queries).**

| Method | Recall@3 | MRR | Hit@3 | Type |
|--------|----------|-----|-------|------|
| hash-v1 (Baseline A style) | 0.833 | 0.700 | 0.833 | MEASURED |
| BM25 | 0.967 | 0.850 | 0.967 | MEASURED |
| TF–IDF cosine | 0.933 | 0.856 | 0.933 | MEASURED |

**Table 4. Workflow scenarios (SIMULATED, \(N=6\)).**

| Metric | Value | Type |
|--------|-------|------|
| Task completion rate | 1.00 | SIMULATED |
| Escalation appropriateness | 1.00 | SIMULATED |
| FCR (sim. definition) | 0.833 | SIMULATED |
| Avg auto / manual minutes | 4.0 / 26.2 | SIMULATED (not live productivity) |
| Answer-quality human ratings | — | Not evaluated |
| Sentence-transformer dense retrieval | — | Not evaluated |

**Interpretation.** On this synthetic AssistIQ-shaped test set, TF–IDF classifiers outperformed keyword intent (H1 supported here). Direct route classification outperformed intent+map while oracle+map reached perfect route accuracy, indicating residual map-pipeline error is largely intent error (H2 supported here). BM25 and TF–IDF cosine exceeded hash-v1 on Recall@3/MRR overall, with hash-v1 weaker on paraphrase queries (H3 supported here). Policy scenarios matched gold decisions under simulation; timing reductions are checklist-derived and must not be reported as measured productivity (H4 simulation executed; productivity projected/measured live = Not evaluated).

**Limitations.** Synthetic labels favour patterns related to AssistIQ templates; absolute percentages will not transfer unchanged to production traffic. Corpus and query counts are small. No human RAG answer study was run. Literature SVM/BERT/FCR figures remain external context only.
