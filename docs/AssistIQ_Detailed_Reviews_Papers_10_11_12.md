# AssistIQ — Detailed Paper Reviews (Papers 10, 11, 12)

Use one page per paper for submission. Each Google Scholar link is the **exact paper cluster** (not a keyword search). AssistIQ currently implements Phases 0–4; Phases 5–10 are designed, not claimed as live production numbers.

---

## Paper 10 — Kolagani (2024)

**Title:** Agentic Automation and Work Flow Orchestration in Enterprise SaaS: Effects on Ticket Resolution Time and Employee Productivity in IT Service Management

- **Author:** Sri Hari Deep Kolagani
- **Venue:** *International Journal on Science and Technology (IJSAT)*, Vol. 15, Issue 4, pp. 103–118
- **Published:** 8 November 2024
- **DOI:** https://doi.org/10.71097/ijsat.v15.i4.9876
- **PDF:** https://www.ijsat.org/papers/2024/4/9876.pdf
- **Google Scholar (this paper):** https://scholar.google.com/scholar?cluster=1180192687157703526&hl=en

### Brief discussion

- The paper studies whether **autonomous AI agents** can beat fully manual ITSM on three headline KPIs: ticket resolution time, first-contact resolution (FCR), and employee productivity.
- Research questions: (1) can agent-aided classification/triage/routing cut mean time to resolve; (2) what happens to SLA compliance and workload; (3) does automation raise tickets processed per agent.
- Design is a **quasi-experiment** (not a randomized trial): agent-aided workflow vs manual workflow on **retrospective public datasets**.
- Data sources named in the paper: Hugging Face (e.g. `Tobi-Bueck/customer-support-tickets`, `Console-AI/IT-helpdesk-synthetic-tickets`), Kaggle, and a cited Microsoft Support corpus of about **50,000** tickets covering hardware, software, network, billing, and service failure.
- Models used for classification/routing: Decision Trees, Random Forest, SVM, KNN, and neural networks; evaluation mentions accuracy, precision, recall, F1, plus paired t-tests and regression.
- Workflow comparison covers triage, classification, routing, and in some cases **auto-resolution** — there is no knowledge-base RAG, no RBAC product, and no approval-gated action layer.
- Useful to AssistIQ as **KPI motivation for Phase 7** (resolution time, FCR, SLA, throughput). It is **not** a deployed, examiner-reproducible ITSM platform.

### Results

- **Resolution time (results section):** manual mean **48 hours** → agent-aided **35 hours** (**13 hours saved**). This is the only pair that matches the abstract’s “up to 13 hours.”
- **Resolution time (discussion, conflicting):** later restated as only **20–30 minutes** saved per ticket. Cite the 48→35 figure, and note the contradiction.
- **High-priority tickets:** AI routing is claimed to send urgent tickets to the most suitable agent and improve response time more than the average case.
- **FCR (abstract):** **+53%**. **FCR (results):** manual **60%** → automated **71%** (11 percentage points; about 18% relative). These two claims do **not** match.
- **Agent handling time:** sorting/categorization **12 minutes → 4 minutes (−65%)**, freeing agents for harder tickets.
- **Productivity (abstract / results):** **+22%** tickets processed per agent per day. **Discussion:** restated as **+25%**.
- **SLA compliance:** **80% → 91%** (+11 percentage points), attributed to better priority routing and load balancing.
- **Qualitative claim:** customer call-ins / recontacts fall because first-touch information is better; complex technical tickets still often need humans.
- **External anecdotes (not this experiment):** Microsoft cited as −20% resolution time / −25% agent workload; IBM as +15% FCR / −30% resolution time. Treat these as literature examples, not Kolagani’s own measurements.

### Limitations

- **No live system:** experiment replays public/synthetic tickets; there is no authenticated helpdesk, ticket table, or SLA engine.
- **Dataset gap:** Hugging Face / Kaggle (including synthetic helpdesk sets) do not represent enterprise change-control, RBAC, or multi-policy SLAs. The author asks for broader real ITSM data.
- **Internal metric conflicts:** 13 hours vs 20–30 minutes; +53% FCR vs 60%→71%; +22% vs +25% productivity. An examiner can challenge these numbers.
- **Weak causality:** quasi-experiment, no randomization; “four-week real-time” wording conflicts with “retrospective dataset” design.
- **Unsafe autonomy:** agents are described as auto-resolving tickets with **no approval gate, rollback, or audit trail** — unacceptable for access, password reset, or software install.
- **No grounding:** classification/routing only; no published knowledge retrieval, so answers cannot be cited.
- **Venue / authorship:** single-author IJSAT article; not ACM/IEEE top-tier. Use for motivation, not as gold-standard evidence.

### How AssistIQ is better

- **We built the ITSM core they only simulate.** AssistIQ already has JWT login, roles (`employee`, `agent`, `admin`), ticket CRUD, comments, append-only events, sequential IDs (`TICK-00001`), and priority-linked SLA policies in Neon PostgreSQL.
- **Governance first, then agents.** Phase 7 is specified as allow-listed runbooks + human approval + rollback. Kolagani skips this and lets agents auto-resolve — AssistIQ will not do that for privileged IT actions.
- **Knowledge before generation.** Phase 4 already retrieves **published** document chunks with similarity scores. Kolagani has no RAG path, so an agent cannot show *where* an answer came from.
- **Reproducible for the examiner.** Repository, Alembic migrations, and automated backend tests exist. Kolagani’s Hugging Face replay cannot be marked as a running product.
- **Honest metrics.** AssistIQ does **not** claim 13 hours / 53% FCR. Those figures are inconsistent even inside one paper. Phase 9 will log measurable retrieval/workflow telemetry instead of mixed abstract numbers.
- **Integrated platform, not a classifier notebook.** Ticketing, SLA, RBAC, and knowledge search sit in one FastAPI + React system. Paper 10 never leaves the dataset-comparison layer.

**Submit line:** Kolagani motivates Phase 7 KPIs. AssistIQ is stronger as a real, governable ITSM implementation; we do not adopt his conflicting percentages as targets.

---

## Paper 11 — Xu et al. (2024)

**Title:** Retrieval-Augmented Generation with Knowledge Graphs for Customer Service Question Answering

- **Authors:** Zhentao Xu, Mark Jerome Cruz, Matthew Guevara, Tie Wang, Manasi Deshpande, Xiaofeng Wang, Zheng Li (LinkedIn)
- **Venue:** *Proc. 47th International ACM SIGIR Conference (SIGIR ’24)*, Washington, DC, 14–18 July 2024, pp. 2905–2909
- **DOI:** https://doi.org/10.1145/3626772.3661370
- **Google Scholar (this paper):** https://scholar.google.com/scholar?cluster=16579645722360031819&hl=en
- **Verified:** 23 August 2026 — first Scholar hit for the exact title; ACM PDF; **Cited by 370**

### Brief discussion

- Problem: standard RAG treats Jira-style tickets as **plain text**. Chunking then loses (a) **intra-ticket structure** (summary, description, steps-to-reproduce, solution) and (b) **inter-ticket links** (clone / caused-by / related-to).
- Consequence they name: a ticket that states the *problem* at the top and the *fix* at the bottom can be split, so the model retrieves an incomplete answer.
- Method has two phases:
  - **KG construction:** each ticket becomes a tree of sections (rule parse + LLM parse against a YAML template). Trees are joined by explicit Jira edges and implicit title-embedding similarity (cosine ≥ threshold).
  - **QA:** LLM extracts entities/intent from the user query; E5 embeddings in Qdrant find candidate tickets; an LLM writes a graph query (e.g. Cypher) for the needed subgraph; GPT-4 writes the answer. Text-chunk RAG is the fallback if the graph query fails.
- Control: **same GPT-4 generator and same E5 embedder** for KG-RAG vs text-chunk baseline, so the gain is from structure, not from a bigger model.
- Online: ~**six-month** two-group deployment in LinkedIn customer service (tool used vs traditional manual lookup).
- AssistIQ lesson: **chunking is not a preprocessing detail — it is the retrieval model.** Phase 4 must not split a solution away from its problem statement.

### Results

**Offline retrieval (Table 1)**

- MRR: **0.522 → 0.927** (**+77.6%**)
- Recall@1: **0.400 → 0.860**
- Recall@3: **0.640 → 1.000**
- NDCG@1: **0.400 → 0.860**
- NDCG@3: **0.520 → 0.946**

**Offline generation (Table 2, vs golden solutions)**

- BLEU: **0.057 → 0.377** (+0.32)
- METEOR: **0.279 → 0.613**
- ROUGE: **0.183 → 0.546**

**Online LinkedIn deployment (Table 3)**

- Mean resolution: **40 hours → 15 hours**
- Median (P50): **7 hours → 5 hours** (**−28.6%**)
- P90: **87 hours → 47 hours**
- Interpretation: grounded, structure-aware retrieval can cut real support time — a Phase 6/9 KPI AssistIQ should measure later, not invent now.

### Limitations

- **Closed production:** tickets, KG template, and golden-set size are not released. Results are not independently reproducible.
- **Short industry paper (5 pages):** limited ablation, no public N, little statistical testing around the tables.
- **Schema lock-in:** Jira trees and clone/caused-by edges do not exist in AssistIQ’s current ticket model. A full KG is not Phase 4 scope.
- **Always-on GPT-4:** every query pays LLM cost/latency/privacy; no router that sends easy tickets to a cheap classifier.
- **Not a full ITSM product:** no employee/agent/admin RBAC, no SLA policy engine, no draft-vs-published knowledge rule.
- **Construction cost:** rule + LLM parsing of every ticket is expensive and breaks if the template changes.
- **Fallback still needed:** they keep text-EBR when graph queries fail — the KG is not universally reliable.

### How AssistIQ is better

- **We do not claim better MRR than LinkedIn.** Their 0.927 / −28.6% are real production numbers we have not run. Our advantage is **platform and safety**, not a fake benchmark win.
- **Retrieval before generation.** Phase 4 returns published chunks + scores only. Xu generate with GPT-4 immediately. AssistIQ will not emit uncited LLM answers until Phase 6.
- **RBAC on knowledge.** Draft and archived documents never enter employee search. Xu retrieve historical tickets without a published-document visibility model.
- **Examiner-auditable storage.** Neon holds ticket/KB metadata; Chroma holds vectors; APIs and tests are in the repo. LinkedIn’s Qdrant + graph stack cannot be marked.
- **Planned multi-model routing (Phase 5).** Category/priority can stay on SVM/RF-class models; LLM is reserved for hard QA. Xu pay GPT-4 for every question.
- **We take their scientific point without their lock-in.** Phase 4/6 should use **section-aware / parent-document retrieval** so a fix is not split from its symptom — the same idea as Xu, without requiring a proprietary LinkedIn KG.
- **Full ITSM around retrieval.** Auth, roles, tickets, SLA, and search already coexist. Xu is a customer-service QA component, not a service-desk product.

**Submit line:** Xu proves structure-preserving RAG works in production. AssistIQ is stronger as an open, role-aware ITSM platform that can apply that lesson without GPT-4-only, closed-data design.

---

## Paper 12 — Packowski, Halilovic, Schlotfeldt, and Smith (2024)

**Title:** Optimizing and Evaluating Enterprise Retrieval-Augmented Generation (RAG): A Content Design Perspective

- **Authors:** Sarah Packowski, Inge Halilovic, Jenifer Schlotfeldt, Trish Smith (IBM)
- **Venue:** *Proc. 8th International Conference on Advances in Artificial Intelligence (ICAAI 2024)*, London, 17–19 October 2024, pp. 162–167, ACM
- **DOI:** https://doi.org/10.1145/3704137.3704181
- **Google Scholar (this paper):** https://scholar.google.com/scholar?cluster=2598771697760282171&hl=en
- **Verified:** 23 August 2026 — first Scholar hit for the exact title; ACM PDF; **Cited by 26**; 3 versions

### Brief discussion

- Core argument: RAG papers usually tune **models**. In enterprise docs support, **how you write, chunk, and judge knowledge** often matters more — especially when search and LLMs are **closed-box APIs** you cannot fine-tune.
- Production setting: RAG on the **product-documentation search page**. If the query looks like a natural-language question, users still get normal search hits **plus** a short cited answer. It is **not a chatbot** (no dialog history in the prompt).
- Architecture (modular / model-agnostic):
  - Pre-process input (reject injection / HAP; detect question type: what-is, how-to, troubleshooting).
  - Serve hard-coded or curated FAQs for sensitive/legal items.
  - Rewrite/augment the question (jargon, synonyms).
  - Call a **closed search API**; then ground the LLM on **whole DITA topics** (“small2big” / parent-document retrieval), not arbitrary token windows.
  - Simple prompt: rewrite the topic into a short faithful answer; attach **links to grounding topics**; highlight terms that drove the answer.
- Evaluation is **human-in-the-lead**, not BLEU/ROUGE/LLM-as-judge on Wikipedia quizzes. Reviewers label: valid question; correct class; article exists; search success; good answer.
- AssistIQ lesson: Phase 4 knowledge should be **short, complete, question-driven topics**; Phase 9 should debug *where* the pipeline failed (missing content vs search miss vs bad answer).

### Results

- **Content-rewrite experiment:** 189 Natural Questions items about Earth. Example failure: “pre-industrial CO₂” answered **180 ppm** (glacial value) instead of **280 ppm**. One clarifying edit in the source topic flipped the answer; similar edits raised the set to **100%** correct. Code/edits: https://github.com/spackows/ICAAI-2024_RAG-CD
- **Production coverage (same RAG, two snapshots):**
  - July: **40%** of valid questions had **no topic** that could answer them.
  - Writers filled gaps → December: topics existed for **75%** of valid questions.
- **Search regression (same period):** by December, search **failed to find** the relevant topic **47%** of the time. Human review isolated “article exists = yes, search = fail” so the next fix was search, not the LLM.
- **User behaviour:** natural-language questions rose from **25% → 39%** of search-bar queries; users still mostly type keywords.
- **Feedback is too thin to be the only signal:** ratings on **<1%** of answers, mostly thumbs-down / “unhelpful.”
- **Writing guidelines that improved RAG:** simplify tables; explain graphics in text; add summaries to long procedures; introduce lists with a lead-in sentence; avoid deep nesting.
- **Seven failure points they confirm (Barnett et al.):** missing content; search failure; context-window limits; poor LLM wording; wrong format; vague answers; incomplete answers.

### Limitations

- **Experience report**, not a multi-company randomized experiment.
- **Closed IBM search and LLM APIs** — authors cannot open or retune the retriever/generator; results are stack-specific.
- **Documentation only** — no ticketing, SLA, assignment, or role-scoped incidents.
- **Single-turn by design** — no conversation state, agent workspace, or escalation workflow.
- **User feedback <1%** — quality loops need a review tool, not thumbs alone.
- **Production logs are private.** The NQ rewrite is reproducible; the July–December enterprise numbers are not.

### How AssistIQ is better

- **We own the retrieval stack.** FastAPI + Neon `document_chunks` + Chroma is inspectable; `hash-v1` is a documented Phase 4 placeholder, swap-ready for real embedders in Phase 5. Packowski cannot open their search API.
- **ITSM and knowledge in one RBAC product.** Employees/agents already file tickets under SLA **and** search published KB. Paper 12 only answers documentation questions.
- **Document lifecycle they do not specify.** AssistIQ enforces `draft → published → archived`; only published content is searchable. IBM’s paper does not define employee vs agent vs admin visibility.
- **Retrieval-first, then optional chat.** Phase 4 is search with scores; Phase 6 adds cited generation. They couple search to an LLM on day one.
- **Observability is in the product path.** Phase 4 already logs timestamp, query length, top_k, result count, latency, scores, embedder ID. Phase 9 extends this to faithfulness/tokens — the same “missing article vs search fail vs bad answer” split they built as a side web app.
- **We apply their content rules on our stack.** Write short complete topics; prefer section/parent retrieval over blind 512-token splits; always return source links. That is Packowski’s result without IBM lock-in.
- **We do not claim 100% NQ accuracy.** That score is a rewrite experiment on Wikipedia-style questions, not AssistIQ’s IT FAQ corpus.

**Submit line:** Packowski proves KB quality and human review beat benchmark-chasing. AssistIQ is stronger as an owned, role-aware ITSM + retrieval platform that can apply those lessons with examiner-visible code.

---

## One-line comparison for the examiner

- **Paper 10** motivates workflow KPIs but is a dataset study with conflicting numbers and no safety model.
- **Paper 11** is the strongest RAG evidence (SIGIR, 370 citations) but is closed, GPT-4-only, and not a full ITSM product.
- **Paper 12** is the strongest *content + evaluation* evidence but is docs-only and API-locked.
- **AssistIQ** is the integrated, test-backed, RBAC-governed platform (Phases 0–4 done) that can use all three lessons **without claiming their unverified or non-transferable production percentages**.
