# AssistIQ — Project Report Content Pack
(Structured to match the required format: Problem Statement → Literature Review → Objectives → Plan of Work → Architecture)

---

## 1. Problem Statement

Enterprise IT helpdesks handle a high volume of repetitive, low-complexity issues — password resets, VPN failures, software installation requests, and access unlocks — that consume disproportionate engineer time and delay resolution of genuinely complex problems. Employees face slow first-response times, company knowledge is scattered across wikis and PDFs, and tickets are triaged manually, leading to inconsistent SLAs. Existing AI helpdesk tools reduce some of this load, but as the literature review below shows, they come with real gaps in flexibility, transparency, and depth of automation — which is the gap this project addresses.

**Draft problem statement line:**
"Organizations need an AI-driven IT helpdesk that can understand employee issues in natural language, retrieve accurate answers from internal documentation, autonomously resolve common issues, and transparently escalate complex ones — without the cost, rigidity, and opacity of existing enterprise AI support platforms."

---

## 2. Literature Review

### a. Existing Similar Systems

| System | What it does |
|---|---|
| **ServiceNow Virtual Agent** | Built-in ITSM chatbot deeply integrated with ServiceNow's workflow engine; tickets are created/updated natively within ITSM. |
| **Moveworks** (acquired by ServiceNow, Dec 2025) | <cite index="12-1">Provides a conversational AI engine combining natural-language understanding with enterprise search, now positioned as ServiceNow's front-door AI layer</cite>. Sold both standalone and as a ServiceNow add-on. |
| **Aisera** | <cite index="10-1">Offers a large integration library across ITSM, HR, CRM, and ERP systems, an omnichannel virtual agent, and domain-specific LLMs pre-trained on ITIL workflows</cite>. |
| **Espressive** | <cite index="8-1">An IT-first virtual support agent focused on intent recognition and automating repetitive service-desk requests</cite> rather than broad cross-department automation. |
| **Academic / rule-based chatbot systems** | <cite index="5-1">A systematic review of 53 academic papers on organizational chatbots found they optimize customer service, HR, and internal operations by automating tasks and improving operational efficiency</cite>. |

### b. Their Benefits

- <cite index="3-1">AI-powered chatbots effectively reduce response times and operational costs while improving customer satisfaction, and studies show they can handle up to 70% of routine inquiries</cite>.
- <cite index="18-1">RAG-powered assistants ground their answers in a company's own wikis, manuals, and internal documents, making responses more trustworthy and specific than a generic model reply</cite>, which is exactly the mechanism proposed for AssistIQ's Knowledge Agent.
- <cite index="14-1">RAG overcomes the "knowledge cutoff" problem of static LLMs by dynamically connecting the model to current, external data at query time</cite>.
- Enterprise platforms like Aisera and Moveworks offer <cite index="10-1">omnichannel support across Slack, Teams, email, and voice, with prebuilt workflows for common ITSM scenarios</cite>.

### c. Their Limitations

- <cite index="9-1">Moveworks' answer quality depends heavily on documentation maturity — if an organization's knowledge base is poorly maintained, the AI struggles to give reliable answers</cite>. This directly motivates a careful RAG chunking/retrieval design in AssistIQ.
- <cite index="13-1">Existing platforms in this space are limited in scope (IT, HR, and facilities only) and in depth — they focus on conversation and routing rather than genuine multi-step task execution</cite>. AssistIQ's Automation Agent (via function/tool calling) is designed specifically to close this gap.
- <cite index="8-1">Enterprise-grade platforms can be expensive for smaller organizations, and deep customization often requires significant configuration effort</cite> — relevant since AssistIQ is built on general-purpose LLM APIs rather than a paid proprietary platform.
- <cite index="15-1">Standard RAG pipelines can struggle with long-tail knowledge and hallucinate when retrieval fails, and static retrieve-then-generate designs don't handle complex, multi-hop queries well</cite> — a known risk to explicitly address in the Knowledge Agent's design (citations, confidence thresholds, fallback to human escalation).
- <cite index="5-1">Organizational chatbot adoption still faces barriers around trust, ethical concerns, and integration challenges</cite> — motivating AssistIQ's transparent, per-agent (rather than single black-box) architecture.
- <cite index="3-1">Even well-performing chatbots need a balanced approach combining automation with human support, since fully automated systems struggle with complex needs</cite> — motivating a clear escalation path from AI agents to human engineers.

---

## 3. Objective of Your Project

*(Each objective is written to explicitly counter one of the limitations identified above.)*

1. **Ground every answer in verified company documentation** — build a RAG-based Knowledge Agent with citation-backed responses, reducing reliance on the AI "guessing" when documentation is incomplete (addresses the documentation-maturity limitation of tools like Moveworks).
2. **Move beyond conversation into real task execution** — implement an Automation Agent using function/tool calling to actually perform password resets, VPN fixes, and account unlocks, not just route the request to a human (addresses the "routing, not execution" limitation of existing platforms).
3. **Keep the system affordable and buildable without enterprise licensing** — build entirely on general-purpose LLM APIs (GPT-4/Gemini/Claude) and open tools (LangGraph, ChromaDB, PostgreSQL) instead of a costly proprietary ITSM platform (addresses the cost/customization-effort limitation).
4. **Make agent reasoning transparent and auditable** — use a modular multi-agent architecture (Intent, Diagnostic, Knowledge, Automation, Ticket) instead of a single opaque chatbot, so each decision step can be logged and reviewed (addresses the trust/opacity limitation).
5. **Provide a clear human escalation path** — automatically hand off low-confidence or high-risk cases to a human engineer rather than forcing full automation (addresses the "balanced automation" limitation).

---

## 4. Plan of Work (Objective-wise Timeline)

| Objective | Deliverable | Roadmap Phase(s) |
|---|---|---|
| Foundation | Auth, RBAC, base dashboards | Phase 1–2 |
| Obj. 4 — Transparent multi-agent reasoning | Ticket management + AI chat interface | Phase 3–4 |
| Obj. 1 — Grounded, cited answers | Knowledge Base + RAG pipeline (ChromaDB) | Phase 5 |
| Obj. 4 — Modular agent architecture | Multi-Agent orchestration via LangGraph | Phase 6 |
| Obj. 1 & 4 — Accurate triage | Intelligent ticket classification (priority/category/SLA) | Phase 7 |
| Obj. 2 — Real task execution | Automation Agent (password reset, VPN, unlocks) | Phase 8 |
| Extended capability | Screenshot analysis (vision AI) | Phase 9 |
| Obj. 1 — Context continuity | AI memory across tickets/conversations | Phase 10 |
| Supporting infra | Real-time collaboration (WebSockets) | Phase 11 |
| Obj. 4 — Auditability | Analytics dashboard (KPIs, resolution rate) | Phase 12 |
| Obj. 3 — Low-cost integration | Slack/Teams/Email/Outlook integrations | Phase 13 |
| Obj. 5 — Safe escalation & security | RBAC hardening, audit logs, deployment | Phase 14 |
| Final delivery | Testing, docs, demo, polish | Phase 15 |

*(You can turn this table directly into a Gantt-style timeline slide in your PPT.)*

---

## 5. Architecture / Methodology of the Project

**Flow:**
Employee → React + TypeScript (Frontend) → FastAPI (Backend) → Auth (JWT + RBAC) → AI Orchestrator (LangGraph) → [Intent / Diagnostic / Knowledge / Automation / Ticket Agents] → PostgreSQL + ChromaDB → Analytics Dashboard

**Methodology summary:**
- Each agent is a distinct LLM call with its own system prompt and expected output schema (structured JSON), not a custom-trained model — directly addressing the cost and complexity limitations found in the literature.
- The Knowledge Agent uses a retrieve-then-generate RAG pipeline: relevant document chunks are pulled from ChromaDB before the LLM composes a cited answer, mitigating hallucination risk.
- The Automation Agent uses function/tool calling: the LLM selects which pre-written backend function to invoke; the function itself performs the actual action.
- LangGraph manages state and routing between agents, enabling conditional logic (e.g., escalate to a human if confidence is low) — directly implementing Objective 5.
- All actions are logged for auditability, supporting Objective 4.

---

### Sources referenced (for your literature review citations)
- Uzok, Cadet & Ojukwu (2024), *Leveraging AI-Powered Chatbots to Enhance Customer Service Efficiency*, Computer Science & IT Research Journal — researchgate.net
- *AI-Powered Chatbots in Organizations: A Systematic Literature Review* (2025) — researchgate.net
- Moveworks vs ServiceNow Virtual Agent comparisons — peerspot.com, ravenna.ai, agent.nexus (2026)
- Top Moveworks Alternatives guides — workativ.com, clearfeed.ai (2025–2026)
- *Building Retrieval-Augmented Generation (RAG) for Internal Knowledge Bases* (2025) — researchgate.net
- *AgenticRAG: Agentic Retrieval for Enterprise Knowledge Bases* — arxiv.org
- Aerospike, *Retrieval Augmented Generation for Enterprise AI Systems* (2025)

*(Pull the full PDFs of the ResearchGate/arXiv papers above for your formal literature review citations — these excerpts are enough to identify which papers are relevant.)*
