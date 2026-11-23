# AssistIQ — Review 2 / Final Project Report

**Project Title:** AssistIQ — AI-Enabled Intelligent IT Service Management Platform  
**Report Type:** Review 2 / Final-Year Engineering Project Report  
**Institution:** [Insert institution name]  
**Author(s):** [Insert student name(s)]  
**Supervisor:** [Insert supervisor name]  
**Date:** August 2026  
**Repository:** `assist` (FastAPI backend + React/Vite frontend)

---

## Document Control

| Item | Detail |
|------|--------|
| **Implementation basis** | Repository inspection conducted 21 August 2026 |
| **Implemented phases** | Phase 0, Phase 1, Phase 2, Phase 3, **Phase 4** |
| **Planned phases** | Phase 5 through Phase 10 |
| **Source of truth** | Application code, migrations, tests, and configuration in the repository — not marketing README text |

> **Note:** The root `README.md` describes an earlier Phase 1 snapshot and is partially outdated. This report reflects the **actual repository state** after Phase 4 completion.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Objectives](#2-objectives)
3. [Abstract](#3-abstract)
4. [Literature Survey](#4-literature-survey)
5. [Outcome-Focused Goals](#5-outcome-focused-goals)
6. [Existing Methods and Their Drawbacks](#6-existing-methods-and-their-drawbacks)
7. [Proposed Method](#7-proposed-method)
8. [Feasibility Study](#8-feasibility-study)
9. [System Architecture](#9-system-architecture)
10. [Module Description](#10-module-description)
11. [Hardware and Software Requirements](#11-hardware-and-software-requirements)
12. [Implementation Roadmap / Phases](#12-implementation-roadmap--phases)
13. [Expected Outcomes](#13-expected-outcomes)
14. [Security, Governance and Ethical Considerations](#14-security-governance-and-ethical-considerations)
15. [Limitations](#15-limitations)
16. [Future Scope](#16-future-scope)
17. [Conclusion](#17-conclusion)
18. [References](#18-references)

---

## 1. Introduction

Enterprise IT service management (ITSM) underpins digital workplace productivity. Organizations depend on helpdesks and service desks to resolve incidents, manage access requests, maintain hardware and software assets, and enforce service-level agreements (SLAs). As IT environments grow in complexity — hybrid cloud, remote work, SaaS proliferation — support teams face rising ticket volumes, repetitive triage work, and pressure to deliver faster resolution with limited staffing.

Traditional ITSM platforms provide structured ticketing, workflow routing, and knowledge repositories. However, they often rely heavily on manual classification, keyword search, and human-authored responses. Recent advances in machine learning (ML), deep learning (DL), retrieval-augmented generation (RAG), and large language models (LLMs) offer opportunities to automate structured tasks, ground conversational assistance in organizational knowledge, and orchestrate controlled IT workflows. At the same time, research and industry experience show that unconstrained LLM deployment introduces risks: hallucination, privacy leakage, high latency, unpredictable cost, and insufficient auditability for enterprise operations.

**AssistIQ** is a final-year academic engineering project that designs and implements an enterprise-oriented, AI-enabled ITSM platform. The project follows a phased roadmap: establish a secure full-stack foundation, deliver core ITSM capabilities (authentication, RBAC, ticketing, SLA), build retrieval infrastructure (knowledge base + vector search), and progressively add multi-model AI abstraction, RAG chatbot, workflow automation, secure password reset, observability, and governance.

As of August 2026, the repository implements **Phases 0 through 4**. Phases 5–10 are architecturally specified and partially reflected in placeholder UI routes, configuration placeholders, and design documentation under `assisstai/`, but are **not yet implemented** in application code.

This report presents the Review 2 / final project documentation: problem context, literature synthesis, proposed integrated method, feasibility analysis, architecture, module design, implementation status, expected outcomes, and ethical considerations.

---

## 2. Objectives

The project defines five measurable, outcome-oriented objectives:

**O1 — Deliver an integrated ITSM core with role-aware access control.**  
Implement a modular monolith providing authenticated REST APIs and role-based dashboards for employees, IT agents, and administrators, with authoritative backend RBAC enforcing ticket and knowledge visibility rules.

*Success indicators (implemented):* JWT authentication with refresh-token rotation; three roles (`employee`, `agent`, `admin`); ticket CRUD with role-scoped listing; backend integration tests validating access control.

**O2 — Enable structured ticket lifecycle management with SLA awareness.**  
Provide ticket creation, categorization, prioritization, status transitions, assignment, comments, append-only events, and SLA policy linkage suitable for operational IT support workflows.

*Success indicators (implemented):* Ticket tables and services; sequential ticket numbering (`TICK-00001` pattern); SLA policies by priority; API endpoints for assign/unassign and comments; automated backend tests.

**O3 — Establish knowledge-grounded retrieval infrastructure without premature LLM coupling.**  
Ingest text/Markdown knowledge documents, chunk and embed content, store vectors in ChromaDB and metadata in Neon PostgreSQL, and expose similarity search over **published** documents only.

*Success indicators (implemented):* `knowledge_documents` and `document_chunks` tables; Chroma adapter; chunking/embedding services; search API returning chunks and similarity scores; **no LLM answer generation** in current phase.

**O4 — Design an adaptive multi-level AI architecture (proposed implementation in later phases).**  
Define and subsequently implement a model abstraction layer that routes tasks to lightweight ML, deep learning, or LLM components based on task complexity, confidence, latency, cost, and privacy — avoiding LLM use for tasks better served by classical models.

*Success indicators (planned):* Common model interface; routing policy; telemetry per model class; benchmark harness for classification and RAG metrics.

**O5 — Provide secure, auditable, and measurable AI-assisted IT operations (proposed).**  
Extend the platform with workflow automation (software/access requests, password reset), human approval gates, retrieval/LLM telemetry, and governance controls suitable for academic evaluation and enterprise alignment.

*Success indicators (planned):* Workflow success rate, escalation rate, retrieval precision/recall, faithfulness/groundedness scores, token consumption logs, audit trail completeness.

---

## 3. Abstract

**Problem:** Enterprise IT support teams struggle with manual ticket triage, fragmented knowledge access, long resolution times, and rising operational cost. Existing tools automate record-keeping but often fail to intelligently classify incidents, retrieve authoritative answers, or execute controlled remediation safely.

**Limitations of existing approaches:** Manual helpdesks scale poorly; rule-based systems are brittle; keyword search misses semantic intent; ML classifiers require maintenance but lack conversational capability; LLM-only chatbots risk hallucination, expose sensitive data, and incur high token cost; autonomous agents may bypass human approval and enterprise policy.

**Research/technology gap:** Literature shows effective ticket classification and emerging RAG-based ITSM assistants, but integrated systems combining (a) structured ITSM, (b) governed knowledge retrieval, (c) selective multi-model AI routing, (d) workflow automation with human oversight, and (e) RAG/LLM observability remain under-developed in accessible academic implementations — particularly with clear separation of relational metadata and vector storage.

**Proposed AssistIQ system:** A React + FastAPI modular monolith using **Neon PostgreSQL** for relational data and **ChromaDB** for vectors, implementing authentication/RBAC, ticketing/SLA, and knowledge retrieval (Phase 4 complete). Future phases add model abstraction, LangGraph workflows, secure password reset, and AI analytics.

**Multi-model AI architecture (proposed):** Lightweight ML for classification/priority; DL/transformers for semantic NLP tasks; LLMs for conversational RAG, complex intent, and planning — selected by a routing layer using confidence, latency, and cost constraints.

**RAG:** Published knowledge documents are chunked, embedded, and retrieved via vector similarity; Phase 4 returns retrieval results only. Phase 6 will add LLM generation with citations.

**Secure workflow automation (proposed):** Allow-listed runbooks, approval gates, identity verification, rollback, and audit logging for IT actions.

**AI observability (proposed):** Retrieval latency/scores implemented in Phase 4; LLM token telemetry and RAG evaluation metrics planned for Phase 9.

**Expected outcome:** A demonstrable, academically evaluable ITSM platform that improves self-service and agent efficiency through governed knowledge retrieval and selective AI — without treating every IT task as an LLM problem.

*No experimental production benchmarks (e.g., live MTTR reduction) are claimed in this report; such evaluation is planned after Phases 5–9.*

---

## 4. Literature Survey

This survey analyzes **twelve verified research publications** (2022–2024, plus foundational RAG context where cited by included works) relevant to AssistIQ. Papers 11–12 were identified via Consensus (consensus.app, August 2026) and independently verified on Google Scholar plus ACM Digital Library / DOI resolvers. Full bibliographic verification details, per-paper methodology, and the literature matrix are provided in `docs/AssistIQ_Literature_Matrix.md`.

### 4.1 Individual Paper Summaries

#### Paper 1 — Fuchs, Drieschner, and Wittges (2022)

Fuchs et al. conduct a narrative literature review of machine learning applied to support ticket systems. Searching Scopus, IEEE Xplore, Ebsco, and Web of Science, they find incident management automation as the dominant topic, followed by escalation prediction and sentiment analysis. SVM appears most frequently for ticket classification and often achieves the best reported accuracy (typically 80%–90% across reviewed studies, with individual reports from 63% to 98%). Random Forest is the second most common approach. The review concludes that ML can reduce manual distribution effort but highlights dataset dependence and limited cross-study comparability.

**Relevance to AssistIQ:** Establishes evidence for Phase 5 lightweight ML on ticket metadata and text.

#### Paper 2 — Dlodlo and Sibanda (2023)

This IEEE conference study automates IT helpdesk ticket classification using KNN, SVM, and Random Forest with hyperparameter tuning and under-sampling for class imbalance. Tuned SVM achieves **94.6% accuracy**, outperforming other tuned models. The authors argue automated classification can shorten resolution time and improve satisfaction.

**Relevance to AssistIQ:** Supports SVM/RF as baseline classifiers for AssistIQ ticket categories.

#### Paper 3 — Feng et al. (2023)

Using real cloud production tickets, the authors apply PCA, K-means, and LDA for clustering, and a pre-trained BERT model for dispatch-department classification. Domain-knowledge preprocessing is reported as critical. The BERT classifier achieves **86% accuracy** for routing.

**Relevance to AssistIQ:** Informs Phase 5 DL path and Phase 4 text normalization/chunking quality.

#### Paper 4 — Benitez Pereira et al. (2023)

The authors build a supervised ML classifier for IT support tickets across seven categories, reporting **75% average precision**, and deliver a web prototype for analyst use with reproducible artifacts.

**Relevance to AssistIQ:** Validates full-stack ML ticketing integrated with a web UI — analogous to AssistIQ’s architecture.

#### Paper 5 — Schmidt, Alt, and Zimmermann (2024)

Using Design Science Research, this ICIS short paper proposes a generative assistant combining RAG and vector databases for ITSM incident management. Preliminary Microsoft Knowledge Base testing reports **90.91% accuracy** in identifying relevant documentation. Metrics include escalation rate, self-service resolution, first-contact resolution, and average resolution time.

**Relevance to AssistIQ:** Direct academic precedent for AssistIQ Phases 4 and 6 (vector retrieval + grounded assistance).

#### Paper 6 — Cederlund, Alawadi, and Awaysheh (2024)

In a real IT service desk, LLM+RAG suggests solutions for incoming tickets. A two-week evaluation finds **38.4% solution retention** by technicians. Challenges include integration, unstructured data, and Swedish-language context.

**Relevance to AssistIQ:** Realistic expectation setting for human-in-the-loop RAG (Phase 6) and technician retention as an evaluation metric (Phase 9).

#### Paper 7 — Toro Isaza et al. (2024)

IBM researchers describe a client IT support pipeline combining an encoder-only classifier (IBM Slate 125m fine-tuned on ~14,000 labeled examples) for single-turn case detection with RAG and LLM query generation for grounded recommendations. The paper emphasizes limited public IT-support datasets and privacy/cost constraints on large proprietary LLMs.

**Relevance to AssistIQ:** Exemplifies hybrid routing (classifier + retriever + generator) aligned with AssistIQ’s proposed multi-model design.

#### Paper 8 — Fadnis et al. (2024)

InspectorRAGet is a platform for holistic RAG evaluation: aggregate metrics, instance-level inspection, human and algorithmic judges, and annotator quality analysis. The authors argue aggregate scores alone are insufficient for actionable improvement.

**Relevance to AssistIQ:** Supports Phase 9 evaluation beyond Phase 4 retrieval telemetry.

#### Paper 9 — Wulf and Meierhofer (2024)

Through prototypes on real customer data, the authors explore LLMs for text correction, summarization, and Q&A in technical customer support. They report promising directions but stress **quality-assured implementation** and organizational/data ecosystem changes.

**Relevance to AssistIQ:** Justifies governance-first LLM adoption (Phases 5–10) rather than LLM-first design.

#### Paper 10 — Kolagani (2024)

A quasi-experimental study comparing agent-aided vs manual ITSM workflows on retrospective public datasets reports up to **13 hours saved per ticket**, **53% FCR increase**, and **22% productivity gain**. The author recommends broader datasets and longitudinal study.

**Relevance to AssistIQ:** Motivates Phase 7 agentic workflow orchestration with measurable KPIs — with caution about dataset representativeness.

#### Paper 11 — Xu et al. (2024)

LinkedIn researchers integrate RAG with a knowledge graph built from historical support tickets, preserving intra-ticket section structure and inter-ticket relations that plain-text chunking discards. Against a text-embedding RAG baseline (same GPT-4 generator and E5 embedder), the KG method improves MRR from 0.522 to **0.927** (**+77.6%**), Recall@1 from 0.400 to 0.860, and BLEU from 0.057 to 0.377. A six-month production deployment reduced **median per-issue resolution time by 28.6%** (P50 7 hours → 5 hours; mean 40 hours → 15 hours).

**Relevance to AssistIQ:** Shows that Phase 4 chunking quality and ticket/document structure materially affect retrieval, and that grounded RAG can cut resolution time — a Phase 6/9 KPI. Also cautions that naive fixed-length chunking can split issue descriptions from solutions.

#### Paper 12 — Packowski, Halilovic, Schlotfeldt, and Smith (2024)

IBM content-design researchers report enterprise-scale RAG over product documentation using a modular, model-agnostic architecture (search and LLM as closed-box APIs). They argue that **rewriting knowledge-base content** often outperforms model swapping: minor topic edits raised a 189-question Natural Questions experiment to **100%** correct answers. Human-in-the-lead evaluation over six months raised topic coverage for valid questions from **40% missing content (July) to 75% coverage (December)**, while exposing a later search-failure rate of **47%**. Standard Wikipedia-style RAG benchmarks (BLEU/ROUGE/LLM-as-judge) were not useful for novel user questions.

**Relevance to AssistIQ:** Directly supports Phase 4 published-document quality, parent-document / whole-topic retrieval, citation links, and Phase 9 human-in-the-lead evaluation rather than benchmark-only scores.

### 4.2 Cross-Paper Consensus and Research Gap

#### Theme 1 — Intelligent ticket classification

**Consensus:** Multiple studies (Papers 1–4) agree that supervised ML and transformer models can automate ticket categorization/routing with useful accuracy when domain preprocessing and class imbalance are handled. SVM and Random Forest remain strong baselines; BERT-style models help semantic routing.

**Disagreement / variability:** Reported accuracies range widely (63%–98%) due to dataset differences — no universal model dominates all enterprises.

**Gap:** Few open, standardized ITSM ticket benchmarks for fair comparison across academic prototypes like AssistIQ.

#### Theme 2 — Conversational AI for IT support

**Consensus:** Conversational interfaces can improve satisfaction and reduce load (Papers 5, 6, 9), but adoption depends on integration quality and human trust.

**Gap:** Limited longitudinal studies in live enterprise environments with SLA and security constraints.

#### Theme 3 — RAG and knowledge grounding

**Consensus:** RAG is widely accepted for grounding generative answers in organizational documents (Papers 5–7, 11–12), especially when proprietary LLMs are costly or prohibited. Structured retrieval (knowledge graphs; whole topics instead of naive chunks) and knowledge-base writing quality can outperform model-only tuning (Papers 11–12).

**Gap:** IT-domain corpora are often private; retrieval quality and citation correctness require domain-specific evaluation (Papers 8, 12).

#### Theme 4 — LLM limitations

**Consensus:** LLMs offer flexibility but introduce hallucination, privacy, cost, and integration risks (Papers 6, 7, 9, 12). Quality-assured deployment and human oversight are repeatedly emphasized.

**Gap:** Clear routing policies for when **not** to use an LLM are under-specified in many ITSM papers.

#### Theme 5 — AI workflow automation

**Consensus:** Agentic/automated workflows can improve FCR and productivity (Paper 10), but evidence mixes simulated/retrospective datasets with vendor narratives.

**Gap:** Secure, approval-gated automation with rollback — required in enterprise IT — lacks standardized academic evaluation frameworks.

#### Theme 6 — Model efficiency

**Consensus:** Smaller specialized models (classifiers, retrievers) can reduce cost and latency compared with LLM-only pipelines (Papers 7, 9).

**Gap:** Integrated multi-model orchestration within a single open ITSM platform is rarely implemented end-to-end in academic projects.

#### Theme 7 — AI evaluation and observability

**Consensus:** Aggregate automatic metrics are insufficient; instance-level analysis, human-in-the-lead review, and faithfulness evaluation are necessary (Papers 8, 12).

**Gap:** ITSM-specific RAG evaluation suites and token-cost dashboards are not yet standard practice.

#### Theme 8 — Security and human oversight

**Consensus:** Enterprise AI must address data privacy, grounding, and human escalation (Papers 5, 7, 9, 10).

**Gap:** Few papers combine RBAC-authenticated ITSM cores with vector retrieval and workflow governance in one reproducible codebase.

### 4.3 Research Gap Statement

Therefore, existing research demonstrates that **(a)** ticket classification automation is feasible, **(b)** RAG can ground IT support in organizational knowledge, and **(c)** agentic workflows may improve ITSM KPIs — but there remains a gap in **integrated, governable, multi-model ITSM platforms** that:

1. Separate relational metadata (PostgreSQL) from vector storage (ChromaDB) explicitly  
2. Enforce RBAC at the API layer for tickets and knowledge  
3. Implement retrieval infrastructure before LLM generation  
4. Plan selective model routing rather than LLM-only designs  
5. Provide academic verifiability through automated tests and phased delivery  

**AssistIQ addresses this gap** through a phased, test-backed implementation aligned with enterprise ITSM practice, with Phases 0–4 completed and Phases 5–10 specifying multi-model AI, LangGraph workflows, and observability.

### 4.4 Literature Summary Table

| Paper | Year | Problem | Method | Key Result | Limitation | AssistIQ Link |
|-------|------|---------|--------|------------|------------|---------------|
| Fuchs et al. | 2022 | Manual STS costly | Literature review | SVM/RF commonly best for classification | Heterogeneous datasets | Phase 5 ML scope |
| Dlodlo & Sibanda | 2023 | Manual IT ticket class | SVM/KNN/RF + tuning | 94.6% SVM accuracy | Single study dataset | Ticket category ML |
| Feng et al. | 2023 | Cloud ticket routing | BERT + clustering | 86% routing accuracy | Domain-specific | DL routing |
| Benitez Pereira et al. | 2023 | Topic identification | ML classifier + web app | 75% avg precision | Moderate precision | Full-stack parity |
| Schmidt et al. | 2024 | ITSM doc retrieval | DSR + RAG + vectors | 90.91% doc ID accuracy (prelim.) | Short paper | Phase 4/6 RAG |
| Cederlund et al. | 2024 | Ticket solution suggest | LLM+RAG field eval | 38.4% retention | 2-week study | Human-in-loop |
| Toro Isaza et al. | 2024 | IT support RAG system | Classifier+RAG+LLM | Improved retrieval w/ rerank | Client-specific | Multi-model |
| Fadnis et al. | 2024 | RAG eval tooling gap | InspectorRAGet platform | Instance-level insights | Tooling focus | Phase 9 eval |
| Wulf & Meierhofer | 2024 | LLM in TCS | Prototypes | Qualitative promise | Governance burden | LLM caution |
| Kolagani | 2024 | Agentic ITSM impact | Quasi-experiment | 53% FCR ↑, 22% productivity ↑ | Public datasets | Phase 7 workflows |
| Xu et al. | 2024 | Ticket RAG ignores structure | KG-RAG + EBR | MRR +77.6%; 28.6% faster P50 | LinkedIn-specific KG | Phase 4/6 structured retrieval |
| Packowski et al. | 2024 | Enterprise RAG content/eval | Modular RAG + human eval | Content rewrite → 100% NQ; 75% topic coverage | Closed-box APIs | Phase 4 KB quality; Phase 9 eval |

*See `docs/AssistIQ_Literature_Matrix.md` for DOIs, URLs, and verification status.*

---

## 5. Outcome-Focused Goals

| # | Goal | Metric (proposed unless marked implemented) | Status |
|---|------|---------------------------------------------|--------|
| G1 | Improve IT self-service through governed knowledge retrieval | Retrieval success rate; search latency (ms); user task completion for published KB search | **Partial** — search API + UI implemented; user studies not yet conducted |
| G2 | Reduce ticket handling friction | Mean time to triage; ticket creation-to-assignment time; SLA breach rate | **Partial** — ticketing/SLA implemented; baseline metrics not yet collected |
| G3 | Route tasks to appropriate model class | % tasks handled by ML vs DL vs LLM; routing confidence threshold compliance | **Planned** — Phase 5 |
| G4 | Enable secure, approval-gated automation | Workflow success rate; rollback success rate; unauthorized action rate (target: 0) | **Planned** — Phases 7–8 |
| G5 | Measure AI quality and cost | Classification F1; retrieval precision@k/recall@k; faithfulness; token consumption; cost per query | **Partial** — retrieval telemetry in Phase 4; LLM metrics planned Phase 9 |

**Proposed target examples (not yet validated experimentally):**

- Ticket classification: F1 ≥ 0.80 on held-out organizational dataset (Phase 5)  
- Retrieval: precision@5 ≥ 0.70 on curated IT FAQ benchmark (Phase 9)  
- RAG faithfulness: ≥ 0.85 on labeled Q&A set (Phase 9)  
- P95 search latency: < 500 ms excluding LLM generation (Phase 4 infrastructure target)  
- LLM answer latency: P95 < 5 s with citation attachment (Phase 6 target)

---

## 6. Existing Methods and Their Drawbacks

### 6.1 Method-by-Method Analysis

#### A. Manual helpdesk

- **How it works:** Human agents triage tickets, respond to users, and escalate complex cases.
- **Strengths:** Strong judgment; handles novel and ambiguous situations well.
- **Limitations:** Slow, labour-intensive, expensive, and inconsistent under volume.
- **Security:** Strong human control over sensitive actions.
- **Scalability:** Poor during ticket spikes or staff shortages.
- **Explainability:** High — decisions can be discussed and justified.
- **Cost:** High ongoing labour cost.
- **Latency:** Bounded by human response time.

#### B. Rule-based systems

- **How it works:** Predefined if–then rules route tickets or trigger automated checks.
- **Strengths:** Deterministic, predictable, and auditable when rules are well documented.
- **Limitations:** Brittle; rules require constant maintenance as IT environments change.
- **Security:** Good when rules enforce safe, allow-listed actions only.
- **Scalability:** Moderate — handles volume better than manual triage but degrades as rule sets grow.
- **Explainability:** High — rule paths are traceable.
- **Cost:** Low compute cost; high maintenance cost over time.
- **Latency:** Low for automated rule evaluation.

#### C. Keyword / search-based knowledge systems

- **How it works:** Users search a knowledge base using keywords or basic full-text search.
- **Strengths:** Simple to deploy; fast lookup when exact terms match.
- **Limitations:** Misses semantic paraphrase and synonym queries; poor relevance ranking.
- **Security:** Search indexes must respect RBAC and document publication status.
- **Scalability:** Good for read-heavy workloads.
- **Explainability:** Moderate — results are traceable to indexed documents.
- **Cost:** Low infrastructure cost.
- **Latency:** Low for indexed queries.

#### D. ML-based ticket classification

- **How it works:** Supervised models (e.g., SVM, Random Forest, XGBoost) predict category, priority, or routing from ticket text and metadata.
- **Strengths:** Fast, low-cost inference; strong performance on structured classification tasks.
- **Limitations:** Requires labelled training data; accuracy drifts as ticket patterns change.
- **Security:** Model access does not automatically imply data exposure if APIs are gated.
- **Scalability:** Good — batch and real-time inference are inexpensive.
- **Explainability:** Moderate — feature importance and confusion matrices aid analysis.
- **Cost:** Low training and inference cost.
- **Latency:** Low (milliseconds to tens of milliseconds).

#### E. Deep-learning NLP systems

- **How it works:** Transformer models (e.g., BERT-style encoders) perform semantic classification, similarity, or entity extraction.
- **Strengths:** Strong semantic understanding compared with classical ML on free text.
- **Limitations:** Higher training/serving cost; model opacity; domain adaptation required.
- **Security:** Depends on model hosting, supply chain, and data residency choices.
- **Scalability:** Good with appropriate GPU/CPU serving infrastructure.
- **Explainability:** Lower than classical ML unless augmented with attention or attribution tools.
- **Cost:** Medium to high (compute, retraining).
- **Latency:** Medium (tens to hundreds of milliseconds).

#### F. LLM-only systems

- **How it works:** A large language model handles classification, retrieval, and answer generation through prompting alone.
- **Strengths:** Flexible natural-language understanding and generation across diverse tasks.
- **Limitations:** Hallucination, high token cost, privacy concerns, and inconsistent factual grounding.
- **Security:** Prompt injection and data leakage are significant risks without guardrails.
- **Scalability:** Limited by API rate limits and per-token pricing at scale.
- **Explainability:** Low — reasoning is often opaque.
- **Cost:** High at volume due to token consumption.
- **Latency:** High (seconds or more per request).

#### G. RAG systems

- **How it works:** Retrieve relevant documents from a knowledge base, then generate an answer conditioned on retrieved context.
- **Strengths:** Grounded responses; knowledge base can be updated without full model retraining.
- **Limitations:** Poor retrieval leads to poor answers; pipeline complexity; citation quality varies.
- **Security:** Must enforce RBAC on retrieved content; draft or restricted documents must not leak.
- **Scalability:** Depends on vector index size, embedder choice, and LLM serving capacity.
- **Explainability:** Improved when citations to source chunks are returned.
- **Cost:** Medium — retrieval is cheaper than generation, but LLM calls still add cost.
- **Latency:** Medium to high (retrieval + generation).

#### H. Autonomous AI agents

- **How it works:** Agents plan and execute multi-step actions across tools (ticketing, IAM, runbooks) with varying degrees of autonomy.
- **Strengths:** Potential for end-to-end automation of repetitive IT workflows.
- **Limitations:** Highest risk of unsafe or unintended actions without approval gates and rollback.
- **Security:** Requires strict allow-lists, human approval, audit logging, and least privilege.
- **Scalability:** Complex — orchestration, tool integration, and failure recovery add operational burden.
- **Explainability:** Low unless every agent step is logged and reviewable.
- **Cost:** Variable — depends on number of model calls and tool integrations.
- **Latency:** Variable — multi-step workflows take longer than single-shot classification.

### 6.2 Comparison Summary

AssistIQ’s design explicitly avoids choosing a single method from the list above. Instead:

- **Phases 0–3** implement structured ITSM (A/B baseline replaced by software)  
- **Phase 4** implements (C)+(G) retrieval half — without generation  
- **Phases 5–6** add (D)+(E)+(F) selectively via routing  
- **Phases 7–8** implement governed (H) with approvals  
- **Phases 9–10** add observability and hardening across all methods  

---

## 7. Proposed Method

AssistIQ is proposed as an **integrated ITSM platform**, not an LLM chatbot alone. Nine cooperating layers:

### Layer 1 — ITSM Core (Implemented: Phases 1, 3)

Authentication, RBAC, users, tickets, comments, events, SLA policies. Neon PostgreSQL stores authoritative relational state. FastAPI enforces permissions before business logic executes.

### Layer 2 — Knowledge Management (Implemented: Phase 4)

Admin-managed documents (`draft` → `published` → `archived`). Text/Markdown ingestion, deterministic chunking, embedding abstraction, ChromaDB vector storage, PostgreSQL chunk metadata linked by `chroma_id`. Employees/agents search **published** content only.

### Layer 3 — AI Model Abstraction (Planned: Phase 5)

Common interface for lightweight ML, DL, and LLM backends. Model selection based on task type, confidence, latency, cost, and policy. **Not implemented in repository code.**

### Layer 4 — RAG Engine (Partially implemented)

Retrieval path complete (Phase 4). Generation with citations planned (Phase 6). Current embedding implementation uses deterministic `hash-v1` vectors — a Phase 4 infrastructure placeholder swappable for ML/DL embedders in Phase 5.

### Layer 5 — Conversational AI (Planned: Phase 6)

Intent detection, query processing, context construction, LLM response generation, conversation state, human escalation. Frontend placeholders exist at `/app/employee/chat` and `/app/agent/chat`.

### Layer 6 — Workflow Automation (Planned: Phase 7)

Software/access requests, entity extraction, policy checks, approval gates, allow-listed runbooks, secure execution, validation, rollback.

### Layer 7 — Secure Password Reset (Planned: Phase 8)

Identity verification, risk assessment, IAM integration, confirmation, escalation — not generic LLM text advice.

### Layer 8 — AI Observability (Partial / Planned)

Phase 4 logs retrieval timestamp, query length, top_k, result count, latency, similarity scores, embedding model ID. LLM token telemetry planned Phase 9.

### Layer 9 — Governance (Partial / Planned)

RBAC and auth audit events implemented. Approval controls, rollback engine, full audit explorer UI planned Phases 7–10.

### 7.1 Adaptive Multi-Model AI Architecture (Proposed)

```
USER REQUEST
      ↓
INTENT / TASK ANALYSIS
      ↓
MODEL SELECTION LAYER
      ↓
 ┌──────────────┬────────────────┬──────────────┐
 │              │                │
 ▼              ▼                ▼
Lightweight ML  Deep Learning    LLM
(ticket class,  (semantic NLP,   (RAG answers,
 priority,       transformers)    planning, chat)
 escalation)
 │              │                │
 └──────────────┴────────────────┘
                ↓
         Result + Confidence
                ↓
       Evaluation / Telemetry
```

**Why not LLM for everything?**

| Factor | Lightweight ML | Deep Learning | LLM |
|--------|----------------|---------------|-----|
| Latency | Milliseconds | Tens–hundreds ms | Seconds+ |
| Cost | Very low | Medium | Token-based, high at scale |
| Explainability | Higher (features) | Moderate | Lower |
| Best tasks | Structured classification | Semantic similarity/classification | Language generation, complex intent |
| Privacy | On-prem friendly | Model-dependent | Often external API |

**Current implementation status:** No model-selection layer exists in code. Phase 4 embedding service (`HashEmbeddingService`) demonstrates abstraction only. Phase 5 will introduce routing.

---

## 8. Feasibility Study

### A. Technical Feasibility — **High**

Phases 0–4 are implemented and tested (50 backend pytest cases, 13 frontend vitest cases, TypeScript build passing). Stack components are mature: FastAPI, SQLAlchemy 2.x async, Alembic, React 18, Vite, ChromaDB. Neon provides managed PostgreSQL with SSL. Architecture avoids frontend database access.

### B. Economic Feasibility — **High for academic scope**

Development uses free-tier/eligible academic cloud (Neon dev branch), local Chroma persistence, and open-source frameworks. LLM API costs can be controlled in later phases via model routing and caching. No Docker requirement reduces infrastructure overhead for development.

### C. Operational Feasibility — **Moderate**

Core ITSM workflows are operable by three roles today. Full operational value requires Phases 6–8 (chatbot, workflows). Seed scripts exist for users and SLA policies. Admin user CRUD and analytics dashboards remain placeholders.

### D. Security Feasibility — **Moderate ( improving across phases)**

JWT + HttpOnly refresh cookies, bcrypt password hashing, RBAC dependencies, and auth audit events are implemented. Future workflow and LLM phases require additional prompt-injection defenses, secrets management, and IAM integration — planned but not present.

### E. Academic / Project Feasibility — **High**

Phased delivery maps to academic review milestones (Review 1: foundation/auth; Review 2: ITSM + RAG foundation; Final: AI workflows + evaluation). Each phase has testable acceptance criteria. Scope is ambitious but bounded by explicit “do not implement yet” lists per phase.

---

## 9. System Architecture

### 9.1 Logical Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Browser — React 18 + Vite + TypeScript + TailwindCSS   │
│  Role routes: /app/employee | /app/agent | /app/admin   │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTPS REST (JSON)
                            │ Bearer access token + HttpOnly refresh cookie
                            ▼
┌─────────────────────────────────────────────────────────┐
│  FastAPI Modular Monolith (127.0.0.1:18765)             │
│  ┌─────────────┬──────────────┬───────────────────────┐ │
│  │ Auth/RBAC   │ Ticketing+SLA│ Knowledge Base (P4)   │ │
│  │ (P1)        │ (P3)         │ chunk/embed/search    │ │
│  ├─────────────┴──────────────┴───────────────────────┤ │
│  │ Planned: Model Abstraction | RAG Gen | LangGraph   │ │
│  │ Planned: Workflows | Password Reset | Observability│ │
│  └─────────────────────────────────────────────────────┘ │
└───────────────┬─────────────────────────┬───────────────┘
                │ asyncpg + SQLAlchemy      │ Chroma adapter
                ▼                           ▼
     ┌──────────────────────┐    ┌──────────────────────┐
     │ Neon PostgreSQL      │    │ ChromaDB (local)     │
     │ (ONLY relational DB) │    │ backend/data/chroma/ │
     │ Metadata + tickets   │    │ Vectors ONLY         │
     └──────────────────────┘    └──────────────────────┘
```

### 9.2 Architectural Rules (Locked)

| Rule | Status |
|------|--------|
| Neon PostgreSQL — sole relational database | Enforced |
| ChromaDB — vectors only | Enforced (Phase 4) |
| No pgvector, SQLite, MongoDB, Supabase | Enforced |
| Frontend never accesses DB/Chroma directly | Enforced |
| LangGraph inside FastAPI (future) | Planned |
| No Docker required for dev | Current practice |

### 9.3 Implemented API Surface (August 2026)

| Router | Prefix | Purpose |
|--------|--------|---------|
| Health | `/health`, `/api/v1/ready` | Liveness/readiness |
| Auth | `/api/v1/auth/*` | Login, refresh, logout, me |
| Tickets | `/api/v1/tickets/*` | Ticket lifecycle |
| Knowledge | `/api/v1/knowledge/*` | KB CRUD, publish, archive, search |

### 9.4 Database Migrations

| Migration | Content |
|-----------|---------|
| `0001_bootstrap` | Alembic foundation |
| `0002_auth_users_refresh_tokens` | Users, refresh tokens |
| `0003_auth_audit_events` | Auth audit events |
| `0004_ticketing` | SLA policies, tickets, events, comments |
| `0005_knowledge_base` | knowledge_documents, document_chunks |

---

## 10. Module Description

### Module 1 — Authentication and RBAC

- **Purpose:** Secure user access and enforce role-based permissions across all APIs.
- **Inputs:** Login credentials; JWT access tokens; refresh cookies.
- **Processing:** Password verification (bcrypt), token issuance and rotation, role validation on each request.
- **Outputs:** Access token, HttpOnly refresh cookie, HTTP 401/403 on unauthorized access.
- **Technologies:** FastAPI, PyJWT, bcrypt.
- **Dependencies:** `users` table, auth audit service.
- **Status:** **Implemented** (Phase 1).

### Module 2 — IT Ticket Management

- **Purpose:** Track incidents and service requests through a structured lifecycle.
- **Inputs:** Ticket create/update payloads; assignment and comment requests.
- **Processing:** Validation, SLA policy linkage, status transitions, append-only event recording.
- **Outputs:** Tickets, comments, ticket events, sequential ticket numbers (`TICK-00001`, …).
- **Technologies:** SQLAlchemy, FastAPI, PostgreSQL (Neon).
- **Dependencies:** Authentication module, SLA policies.
- **Status:** **Implemented** (Phase 3).

### Module 3 — Knowledge Management

- **Purpose:** Ingest, store, and retrieve IT knowledge documents for search.
- **Inputs:** Document title, body (text/Markdown), metadata; search queries with `top_k`.
- **Processing:** Deterministic chunking, embedding, vector storage in ChromaDB, metadata in PostgreSQL; similarity search over **published** documents only.
- **Outputs:** Document records, chunk metadata, ranked retrieval results with similarity scores.
- **Technologies:** ChromaDB, chunking service, embedding service, FastAPI.
- **Dependencies:** Authentication/RBAC, Neon PostgreSQL.
- **Status:** **Implemented** (Phase 4 — retrieval only; no LLM generation).

### Module 4 — AI Model Abstraction

- **Purpose:** Provide a common interface and routing layer for lightweight ML, deep learning, and LLM backends.
- **Inputs:** Task type, features/text, routing policy, confidence thresholds.
- **Processing:** Select appropriate model class based on complexity, latency, cost, and confidence.
- **Outputs:** Prediction or classification result with confidence score and model identifier.
- **Technologies:** scikit-learn, PyTorch, configurable LLM provider (planned).
- **Dependencies:** Telemetry module, task definitions from ticketing and RAG pipelines.
- **Status:** **Planned** (Phase 5).

### Module 5 — RAG Engine

- **Purpose:** Combine retrieval with grounded answer generation and citations.
- **Inputs:** User query, knowledge base index, conversation context (future).
- **Processing:** Retrieve relevant chunks (implemented); construct prompt context; generate cited answer (planned).
- **Outputs:** Retrieved chunks (Phase 4); generated answer with citations (Phase 6).
- **Technologies:** ChromaDB, embedding service, LLM API (planned).
- **Dependencies:** Knowledge Management module.
- **Status:** **Partial** — retrieval complete; generation not yet implemented.

### Module 6 — Conversational AI

- **Purpose:** Provide multi-turn AI-assisted support for employees and agents.
- **Inputs:** User chat messages, session state.
- **Processing:** Intent detection, query reformulation, RAG retrieval, LLM response, escalation triggers.
- **Outputs:** Chat transcript, cited responses, escalation to human agent when needed.
- **Technologies:** React chat UI, LangGraph orchestration (planned), FastAPI backend.
- **Dependencies:** Modules 3, 4, and 5.
- **Status:** **Planned** (Phase 6); UI placeholders exist at `/app/employee/chat` and `/app/agent/chat`.

### Module 7 — AI IT Request Workflow

- **Purpose:** Automate software installation and access requests with human approval.
- **Inputs:** Natural-language request, user identity, policy context.
- **Processing:** Entity extraction, policy check, approval gate, allow-listed runbook execution, validation, rollback on failure.
- **Outputs:** Workflow status, audit log entries, ticket updates.
- **Technologies:** LangGraph (planned), FastAPI services, external runbook integrations.
- **Dependencies:** Authentication, ticketing, audit logging.
- **Status:** **Planned** (Phase 7).

### Module 8 — Secure Password Reset Workflow

- **Purpose:** Govern corporate password reset with identity verification and risk assessment.
- **Inputs:** Reset intent, user identity signals, risk context.
- **Processing:** Multi-factor verification, IAM integration, confirmation step, escalation on anomaly.
- **Outputs:** Reset success/failure status, audit trail; no unsupervised credential change.
- **Technologies:** IAM API integration (planned), workflow orchestration.
- **Dependencies:** Authentication module, risk assessment logic.
- **Status:** **Planned** (Phase 8).

### Module 9 — AI Observability and Evaluation

- **Purpose:** Measure retrieval quality, model performance, latency, and cost across AI components.
- **Inputs:** Retrieval traces, model outputs, token usage (future), labelled evaluation sets.
- **Processing:** Log structured telemetry; compute precision/recall, faithfulness, F1; detect regressions.
- **Outputs:** Internal logs (Phase 4 retrieval); dashboards and alerts (planned Phase 9).
- **Technologies:** Python logging, RAGAS-style metrics (planned), admin analytics UI (planned).
- **Dependencies:** All AI-related modules.
- **Status:** **Partial** — retrieval telemetry implemented; LLM token metrics not yet implemented.

### Module 10 — Administration and Governance

- **Purpose:** Provide administrative control, policy enforcement, and audit visibility.
- **Inputs:** Admin actions (KB management implemented; user/audit management planned).
- **Processing:** RBAC-enforced CRUD, lifecycle transitions (publish/archive), audit event recording.
- **Outputs:** Updated records, auth audit events, governance logs.
- **Technologies:** FastAPI, PostgreSQL (Neon), React admin UI.
- **Dependencies:** Authentication module.
- **Status:** **Partial** — KB admin and auth audits implemented; user management and audit explorer UI planned.

---

## 11. Hardware and Software Requirements

### 11.1 Hardware Requirements

| Component | Minimum (Development) | Recommended (ML/DL experiments) | Required? |
|-----------|----------------------|---------------------------------|-----------|
| CPU | 4 cores, x64 | 8+ cores | **Required** |
| RAM | 8 GB | 16–32 GB | **Required** |
| Storage | 20 GB free (code + Chroma + venv) | 50 GB SSD | **Required** |
| GPU | Not required for Phases 0–4 | NVIDIA GPU with 8+ GB VRAM for DL training | **Optional** |
| Internet | Broadband for Neon, npm, pip | Stable low-latency connection | **Required** |

### 11.2 Software Requirements

| Software | Version (repo-tested) | Purpose | Phase |
|----------|----------------------|---------|-------|
| Windows 10/11 or Linux | — | Development OS | All |
| Python | 3.11+ | Backend runtime | All |
| Node.js | 20+ | Frontend tooling | All |
| React | 18.3 | UI | 2+ |
| TypeScript | 5.6 | Typed frontend | 2+ |
| Vite | 5.4 | Frontend bundler | 0+ |
| FastAPI | ≥0.115 | API framework | 0+ |
| Uvicorn | ≥0.32 | ASGI server | 0+ |
| Neon PostgreSQL | Hosted | Relational DB | 0+ |
| SQLAlchemy | ≥2.0 | ORM (async) | 0+ |
| asyncpg | ≥0.30 | PostgreSQL driver | 0+ |
| Alembic | ≥1.14 | Migrations | 0+ |
| ChromaDB | ≥0.5 | Vector store | 4 |
| PyJWT, bcrypt | — | Auth | 1 |
| pytest, vitest | — | Testing | All |
| LangGraph | — | Workflow orchestration | 7 (planned) |
| scikit-learn | — | Lightweight ML | 5 (planned) |
| PyTorch | — | Deep learning | 5 (planned) |
| Configurable LLM provider | — | Generation | 6 (planned) |
| Git | — | Version control | All |

---

## 12. Implementation Roadmap / Phases

### 12.1 Full Roadmap (Phase 0–10)

| Phase | Name | Scope | Status |
|-------|------|-------|--------|
| **0** | Foundation | Repo structure, FastAPI, React+Vite, Neon, SQLAlchemy async, Alembic, health/ready | ✅ **Completed** |
| **1** | Authentication + RBAC | Users, JWT, refresh tokens, roles, audit events | ✅ **Completed** |
| **2** | Application Shell | AppShell, TopBar, Sidebar, dashboards, navigation, protected routes | ✅ **Completed** |
| **3** | Ticketing + SLA | Tickets, categories, priority, status, assignment, comments, SLA, events | ✅ **Completed** |
| **4** | Knowledge Base + RAG Foundation | Ingestion, chunking, embeddings, ChromaDB, Neon metadata, retrieval, KB UI | ✅ **Completed** |
| **5** | AI Model Abstraction | ML/DL/LLM interface, model selection, evaluation hooks | ⏳ Planned |
| **6** | RAG Chatbot + LangGraph | Intent, retrieval, LLM generation, citations, escalation | ⏳ Planned |
| **7** | AI IT Request Workflow | Approvals, runbooks, secure execution, rollback | ⏳ Planned |
| **8** | Secure Password Reset | Identity verification, IAM, risk assessment | ⏳ Planned |
| **9** | AI Observability + Evaluation | Token telemetry, RAG metrics, dashboards | ⏳ Planned |
| **10** | Hardening + Governance | Security hardening, deployment, full audit | ⏳ Planned |

### 12.2 Implemented Functionality Summary (Phases 0–4)

**Phase 0 — Foundation**

- FastAPI application factory with CORS, lifespan, structured logging  
- Neon PostgreSQL via async SQLAlchemy + asyncpg (`sslmode=require` validated)  
- Alembic migrations; `/health` and `/api/v1/ready` endpoints  
- React + Vite frontend at `http://127.0.0.1:5173`; backend at `http://127.0.0.1:18765`

**Phase 1 — Authentication + RBAC**

- Roles: `employee`, `agent`, `admin`  
- JWT access tokens (15-minute expiry); HttpOnly refresh cookie with rotation  
- Endpoints: `/api/v1/auth/login`, `/refresh`, `/logout`, `/me`  
- Tables: `users`, `refresh_tokens`, `audit_events`  
- Seed script: `backend/scripts/seed_users.py`

**Phase 2 — Application Shell**

- `AppShell`, `TopBar`, `Sidebar`, shared UI primitives (`Button`, `Input`, `Badge`, `PageHeader`, `Panel`, `EmptyState`, `LoadingState`, `Toast`)  
- Role dashboards and protected routing  
- Navigation configuration in `frontend/src/lib/navigation.ts`

**Phase 3 — Ticketing + SLA**

- Tables: `sla_policies`, `tickets`, `ticket_events`, `ticket_comments`  
- Categories: `network`, `access`, `hardware`, `software`, `other`  
- Statuses: `open`, `in_progress`, `pending`, `resolved`, `closed`  
- Priorities: `low`, `medium`, `high`, `critical`  
- Ticket numbering via PostgreSQL sequence (`TICK-00001`, …)  
- Services: `sla_service.py`, `ticket_service.py`; API: `backend/app/api/v1/tickets.py`  
- Frontend ticket pages for all three roles  
- Seed script: `backend/scripts/seed_sla_policies.py`

**Phase 4 — Knowledge Base + RAG Foundation**

- Tables: `knowledge_documents`, `document_chunks` (migration `0005_knowledge_base`)  
- Document lifecycle: `draft`, `published`, `archived`  
- Services: `chunking_service.py`, `embedding_service.py` (`hash-v1` deterministic embeddings), `knowledge_base_service.py`  
- Adapter: `backend/app/adapters/chroma.py` — persistent storage at `backend/data/chroma/` (gitignored)  
- API: full admin CRUD, publish, archive, delete; `POST /api/v1/knowledge/search` (retrieval only — **no LLM**)  
- RBAC: employees/agents — search and view published only; admin — full management  
- Retrieval telemetry: `retrieval_telemetry.py` (latency, scores, model ID — no LLM token metrics)  
- Frontend: `/app/employee/knowledge`, `/app/agent/knowledge`, `/app/admin/knowledge` (+ new, detail)  
- Tests: chunking, embedding, Chroma adapter, knowledge API/RBAC tests  
- **Explicitly not implemented in Phase 4:** LangGraph, LangChain, LLM calls, chatbot answer generation

### 12.3 Verification Evidence

| Check | Result |
|-------|--------|
| Backend pytest | 50 passed (August 2026) |
| Frontend vitest | 13 passed |
| TypeScript production build | Pass |
| Alembic head | `0005_knowledge_base` |

---

## 13. Expected Outcomes

Upon completion of all planned phases, AssistIQ is expected to deliver:

1. **Centralized IT support surface** — Single authenticated portal for tickets, knowledge, and (future) AI assistance  
2. **Improved ticket operations** — Structured lifecycle, SLA awareness, role-appropriate views  
3. **Knowledge-grounded assistance** — Retrieval-backed answers with citations, reducing undocumented troubleshooting  
4. **Appropriate model selection** — Lower cost/latency for classification; LLM reserved for language-intensive tasks  
5. **Reduced repetitive workload** — Automation of triage, search, and allow-listed remediation  
6. **Secure automation** — Human approval, audit trails, rollback for sensitive workflows  
7. **Measurable AI performance** — Classification metrics, retrieval quality, faithfulness, token/cost tracking  
8. **Traceability** — Append-only ticket events, auth audits, workflow logs  
9. **Governance alignment** — RBAC, least privilege, escalation paths  

**Current demonstrable outcomes (Phases 0–4 only):** working auth, ticketing, SLA, KB management, and semantic-hash retrieval search — suitable for Review 2 demonstration without claiming LLM or workflow automation results.

---

## 14. Security, Governance and Ethical Considerations

| Area | Implemented | Planned |
|------|-------------|---------|
| RBAC (employee/agent/admin) | ✅ Backend authoritative | Extend to workflow approvals |
| JWT + refresh rotation | ✅ HttpOnly cookie path scoped | Production `COOKIE_SECURE=true` |
| Password hashing | ✅ bcrypt | — |
| Auth audit events | ✅ login/logout/refresh/failures | Full audit explorer UI |
| Least privilege | ✅ Role-scoped tickets/KB | Workflow scopes |
| Published-only retrieval | ✅ Draft/archived excluded | — |
| Human approval for automation | — | Phase 7 |
| Allow-listed runbooks | — | Phase 7 |
| Identity verification (password reset) | — | Phase 8 |
| Prompt injection mitigation | — | Phase 6+ input sanitization, retrieval filters |
| Hallucination risk | Mitigated in P4 (no generation) | Citations + faithfulness eval P6/P9 |
| Sensitive data in logs | Retrieval logs omit full document bodies | Expand redaction policy |
| AI accountability | Partial telemetry | Phase 9 dashboards |
| Data privacy | Neon SSL; secrets in `.env` gitignored | LLM data residency policy |

**Ethical considerations:** IT support AI must not autonomously perform irreversible actions (password changes, software installs) without verified identity and explicit approval. Employees must understand when they interact with retrieval results vs generated advice. Bias in ticket classification models must be monitored across categories.

---

## 15. Limitations

### Current limitations (as implemented)

1. **Phases 5–10 not implemented** — No LLM, LangGraph, workflows, or full observability UI  
2. **Phase 4 embeddings** — `hash-v1` deterministic vectors are infrastructure placeholders, not semantic production embedders  
3. **No LLM answer generation** — Search returns chunks only  
4. **README outdated** — Root README still describes Phase 1 scope; report supersedes for accuracy  
5. **Prototype infrastructure** — Local Chroma persistence; not yet clustered HA deployment  
6. **No live user study** — Ticket/KB efficiency gains not empirically measured with end users  
7. **Admin placeholders** — Analytics, audit explorer, user management UI not built  

### Anticipated limitations (full system)

8. External LLM dependency cost and latency (Phase 6+)  
9. Knowledge freshness requires re-ingestion on document updates  
10. Retrieval quality depends on chunking/embedder choice  
11. Enterprise IAM/runbook integrations may need APIs unavailable in academic setting  
12. Evaluation requires representative labeled datasets not yet assembled  
13. Hallucination cannot be eliminated — only measured and mitigated  

---

## 16. Future Scope

- Replace `hash-v1` with trainable or pretrained embedders under `EmbeddingService` abstraction  
- Implement Phase 5 model routing with scikit-learn/XGBoost baselines for ticket classification  
- Add LangGraph conversational and workflow graphs inside FastAPI  
- Expand document ingestion (PDF/DOCX) with parsing pipelines  
- Build admin analytics and audit explorer on existing `audit_events`  
- Integrate RAGAS-style evaluation and CI/CD quality gates (Phase 9)  
- Multilingual KB and query support  
- Production deployment hardening (HTTPS, secrets manager, rate limiting)  
- Continuous model evaluation and drift detection on ticket/KB data  
- Additional automated workflows (access provisioning, software request fulfillment)

---

## 17. Conclusion

Enterprise IT support faces persistent challenges: manual triage overhead, fragmented knowledge, escalating ticket volumes, and pressure to adopt AI without sacrificing security. Literature from 2022–2024 confirms that machine learning improves ticket classification, RAG grounds generative assistance in organizational documents, and agentic workflows may enhance ITSM KPIs — yet gaps remain in integrated, governable, multi-model platforms with verifiable phased delivery.

AssistIQ responds with a modular monolith architecture: React frontend, FastAPI backend, Neon PostgreSQL for relational integrity, and ChromaDB for vector retrieval. **Phases 0 through 4 are complete**, providing authentication/RBAC, application shell, ticketing with SLA, and knowledge base retrieval infrastructure with automated tests. The project deliberately implements retrieval before generation and reserves LLMs for later phases, aligning with research caution about cost, privacy, and hallucination.

The proposed adaptive multi-model architecture — routing tasks to lightweight ML, deep learning, or LLMs based on complexity and confidence — addresses the inefficiency of LLM-only designs. Planned LangGraph workflows, secure password reset, and AI observability extend the platform toward enterprise-grade governance.

AssistIQ’s expected academic contribution is a **reproducible, test-backed, phased ITSM+AI reference implementation** with explicit separation of concerns between metadata, vectors, and (future) generation — suitable for final-year evaluation and as a foundation for production-oriented extension.

---

## 18. References

IEEE-style references for the twelve literature survey papers. DOIs and URLs verified August 2026. Papers [11]–[12] were sourced from Consensus and confirmed on Google Scholar.

[1] S. Fuchs, C. Drieschner, and H. Wittges, "Improving Support Ticket Systems Using Machine Learning: A Literature Review," in *Proc. 55th Hawaii Int. Conf. System Sciences (HICSS)*, 2022, pp. 1–10. DOI: [10.24251/HICSS.2022.238](https://doi.org/10.24251/hicss.2022.238)

[2] P. Dlodlo and T. Sibanda, "Automated Ticket Classification for Information Technology Helpdesks using Machine Learning," in *Proc. 2nd Zimbabwe Conf. Information and Communication Technologies (ZCICT)*, 2023. DOI: [10.1109/ZCICT59466.2023.10528578](https://doi.org/10.1109/zcict59466.2023.10528578)

[3] H. Feng, J. Han, L. Huang, Z. Sheng, and Z. Gong, "Incident and Problem Ticket Clustering and Classification Using Deep Learning," *ZTE Communications*, vol. 21, no. 4, pp. 69–77, 2023. [Online]. Available: https://zte.magtechjournal.com/EN/Y2023/V21/I4/69

[4] L. S. Benitez Pereira, R. Pizzio, S. Bonho, L. M. F. De Souza, and A. C. Arnoni, "Machine Learning for Classification of IT Support Tickets," in *Proc. IEEE CYMAEN*, 2023. DOI: [10.1109/cymaen57228.2023.10051041](https://doi.org/10.1109/cymaen57228.2023.10051041)

[5] R. Schmidt, R. Alt, and A. Zimmermann, "Generative Assistants for Handling Incidents in IT Service Management," in *Proc. Int. Conf. Information Systems (ICIS)*, 2024. [Online]. Available: https://aisel.aisnet.org/icis2024/digtech_fow/digtech_fow/19/

[6] O. Cederlund, S. Alawadi, and F. M. Awaysheh, "LLMRAG: An Optimized Digital Support Service using LLM and Retrieval-Augmented Generation," in *Proc. 9th Int. Conf. Fog and Mobile Edge Computing (FMEC)*, 2024. DOI: [10.1109/fmec62297.2024.10710181](https://doi.org/10.1109/fmec62297.2024.10710181)

[7] P. Toro Isaza et al., "Retrieval Augmented Generation-Based Incident Resolution Recommendation System for IT Support," *arXiv preprint arXiv:2409.13707*, 2024. DOI: [10.48550/arXiv.2409.13707](https://arxiv.org/abs/2409.13707)

[8] K. Fadnis et al., "InspectorRAGet: An Introspection Platform for RAG Evaluation," *arXiv preprint arXiv:2404.17347*, 2024. DOI: [10.48550/arXiv.2404.17347](https://arxiv.org/abs/2404.17347)

[9] J. Wulf and J. Meierhofer, "Utilizing Large Language Models for Automating Technical Customer Support," *arXiv preprint arXiv:2406.01407*, 2024. DOI: [10.48550/arXiv.2406.01407](https://arxiv.org/abs/2406.01407)

[10] S. H. D. Kolagani, "Agentic Automation and Work Flow Orchestration in Enterprise SaaS: Effects on Ticket Resolution Time and Employee Productivity in IT Service Management," *Int. J. Sci. Advanced Technology*, vol. 15, no. 4, 2024. DOI: [10.71097/ijsat.v15.i4.9876](https://doi.org/10.71097/ijsat.v15.i4.9876)

[11] Z. Xu, M. J. Cruz, M. Guevara, T. Wang, M. Deshpande, X. Wang, and Z. Li, "Retrieval-Augmented Generation with Knowledge Graphs for Customer Service Question Answering," in *Proc. 47th Int. ACM SIGIR Conf. Research and Development in Information Retrieval (SIGIR)*, 2024, pp. 2905–2909. DOI: [10.1145/3626772.3661370](https://doi.org/10.1145/3626772.3661370)

[12] S. Packowski, I. Halilovic, J. Schlotfeldt, and T. Smith, "Optimizing and Evaluating Enterprise Retrieval-Augmented Generation (RAG): A Content Design Perspective," in *Proc. 8th Int. Conf. Advances in Artificial Intelligence (ICAAI)*, 2024, pp. 162–167. DOI: [10.1145/3704137.3704181](https://doi.org/10.1145/3704137.3704181)

---

## Appendix A — Repository Structure (Inspection Summary)

```
assist/
├── backend/
│   ├── app/
│   │   ├── adapters/chroma.py
│   │   ├── api/v1/{auth,health,tickets,knowledge}.py
│   │   ├── core/{config,deps,database,security}.py
│   │   ├── models/{user,ticket,knowledge,sla_policy,...}.py
│   │   ├── services/{auth,ticket,sla,knowledge_base,chunking,embedding,...}.py
│   │   └── schemas/{auth,ticket,knowledge}.py
│   ├── alembic/versions/0001..0005
│   ├── tests/ (9 test modules)
│   └── requirements.txt
├── frontend/
│   └── src/{pages,components,lib,context}/...
├── assisstai/          # Reference design docs (not modified by app code)
└── docs/               # This report
```

---

## Appendix B — Placeholder vs Implemented UI Routes

| Route | Status |
|-------|--------|
| `/app/employee/chat` | Placeholder (ComingSoon) |
| `/app/agent/chat` | Placeholder |
| `/app/admin/analytics` | Placeholder |
| `/app/admin/audits` | Placeholder |
| `/app/admin/users` | Placeholder |
| `/app/*/knowledge` | **Implemented** |
| `/app/*/tickets` | **Implemented** |

---

*End of Report*
