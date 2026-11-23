# AssistIQ — Algorithmic Flowcharts (Methodology Figures)

**Purpose.** Compact academic flowcharts of *backend algorithms* implemented in AssistIQ Baseline A.  
**Not included.** Frontend/UI architecture, deployment topology, or proposed (unimplemented) ML methods.  
**Source of truth.** Current repository implementation (intent, routing, hash-v1, Chroma retrieval, confidence, RAG, IT policy, password policy).

---

## FIGURE A — Intent Detection Algorithm

### Figure title
**Figure A.** Ordered keyword intent detection with optional lightweight override.

### Flowchart

```mermaid
flowchart TD
  A([User message x]) --> B[Lowercase / normalize ℓx]
  B --> C[Scan keyword groups in fixed order O]
  C --> D{∃ keyword w ∈ K_I<br/>with w ⊆ ℓx?}
  D -->|Yes| E[Select first matching intent I*]
  D -->|No| F{"?" ∈ x ?"}
  F -->|Yes| G[GENERAL_QUERY]
  F -->|No| H[KNOWLEDGE_QUERY]
  E --> I{I* = KNOWLEDGE_QUERY<br/>and optional model configured?}
  G --> I
  H --> I
  I -->|No| J([Output intent I*])
  I -->|Yes| K[Lightweight hit-rate heuristic<br/>NOT trained SVM / logreg]
  K --> L{Remap only if allowed<br/>by label map?}
  L -->|Yes| M[Override I*]
  L -->|No / error| J
  M --> J

  classDef decision fill:#E8F1F8,stroke:#1F4E79,color:#111
  classDef process fill:#F5F7FA,stroke:#44546A,color:#111
  classDef note fill:#FFF2CC,stroke:#BF8F00,color:#111
  class D,F,I,L decision
  class B,C,E,K,M process
  class G,H,J process
```

**Ordered groups O:**  
(1) HUMAN_ESCALATION → (2) PASSWORD_RESET_REQUEST → (3) SOFTWARE_ACCESS_REQUEST → (4) TICKET_CREATION_REQUEST → (5) TICKET_QUERY → (6) KNOWLEDGE_QUERY

### Mathematical representation

Let \(\ell(x)\) be the lowercased message and \(K_I\) the keyword set for intent \(I\). AssistIQ uses **substring** containment (not bag-of-tokens equality):

\[
I^{*}(x)=\min_{\prec}\{\,I\in O:\exists\,w\in K_I\text{ with }w\subseteq \ell(x)\,\}
\]

where \(\prec\) is the fixed order on \(O\). Fallback:

\[
I^{*}(x)=\begin{cases}
\texttt{GENERAL\_QUERY}, & \text{no keyword hit and ``?''}\in x,\\
\texttt{KNOWLEDGE\_QUERY}, & \text{no keyword hit otherwise.}
\end{cases}
\]

Optional override applies **only if** \(I^{*}=\texttt{KNOWLEDGE\_QUERY}\) and a lightweight registry model is configured; the adapter scores label keyword hit-rates and is **not** a fitted SVM/logistic model.

### Short explanation
Intent labels drive routing. The detector is a deterministic lexical heuristic: the first matching keyword group wins. That keeps Baseline A inspectable, but paraphrase-heavy utterances that avoid listed substrings fall through to general or knowledge intents unless the optional override remaps them.

### Figure caption
**Figure A.** Keyword-based intent detection in AssistIQ Baseline A (ordered substring match, “?” fallback, optional lightweight hit-rate override only for `knowledge_query`).

---

## FIGURE B — Deterministic Request Routing

### Figure title
**Figure B.** Dictionary-based intent-to-workflow routing.

### Flowchart

```mermaid
flowchart TD
  A([Detected intent c]) --> B[Dictionary lookup]
  B --> C["r(c) = INTENT_ROUTE_MAP[c]"]
  C --> D{c in map?}
  D -->|No| U[handle_unsupported]
  D -->|Yes| T[Mapped workflow node]

  subgraph MAP["INTENT_ROUTE_MAP (deterministic)"]
    direction TB
    M1[knowledge_query → retrieve_context]
    M2[general_query → retrieve_context]
    M3[ticket_query → retrieve_ticket_context]
    M4[ticket_creation_request → retrieve_ticket_context]
    M5[password_reset_request → start_password_reset]
    M6[software_access_request → start_it_request]
    M7[human_escalation → escalate]
    M8[unsupported → handle_unsupported]
  end

  T -.-> MAP
  U --> Z([Route node])
  MAP --> Z

  classDef decision fill:#E8F1F8,stroke:#1F4E79
  classDef process fill:#F5F7FA,stroke:#44546A
  class D decision
  class B,C,T,U process
```

### Mathematical representation

\[
r(c)=\texttt{INTENT\_ROUTE\_MAP}[c],\qquad
r(c)=\texttt{handle\_unsupported}\text{ if }c\notin\mathrm{dom}(\texttt{INTENT\_ROUTE\_MAP}).
\]

### Short explanation
Routing does not classify text a second time. It applies a fixed map from intent strings to LangGraph nodes. Ticket-related chat intents both open ticket-context retrieval; they do **not** insert ticket rows. Errors in routing for Baseline A are therefore largely inherited from intent errors.

### Figure caption
**Figure B.** Deterministic dictionary-based request routing in AssistIQ (`INTENT_ROUTE_MAP`).

---

## FIGURE C — Hash-Based Query Embedding

### Figure title
**Figure C.** Deterministic hash-v1 embedding (\(d=384\)).

### Flowchart

```mermaid
flowchart TD
  A([Normalized query text]) --> B[Whitespace tokenize]
  B --> C[For each token t]
  C --> D["digest = SHA-256(t)"]
  D --> E["For each byte b at index i:<br/>j = (b+i) mod d<br/>v_j ← v_j + 1 + b/255"]
  E --> F{More tokens?}
  F -->|Yes| C
  F -->|No| G["v ∈ R^d , d = 384"]
  G --> H{"∥v∥₂ ≠ 0 ?"}
  H -->|Yes| I["e = v / ∥v∥₂"]
  H -->|No| J[e = 0]
  I --> K([hash-v1 embedding e])
  J --> K

  classDef decision fill:#E8F1F8,stroke:#1F4E79
  classDef math fill:#DEEBF7,stroke:#1F4E79
  classDef process fill:#F5F7FA,stroke:#44546A
  class F,H decision
  class D,E,G,I math
  class B,C process
```

### Mathematical representation

\[
j=(b+i)\bmod d,\quad
v_j\leftarrow v_j+1+\frac{b}{255},\quad
d=384,\quad
e=\frac{v}{\|v\|_2}\ (\|v\|_2\neq 0).
\]

**Label:** Deterministic Hash Embedding — `hash-v1` (no training).

### Short explanation
The embedding is a fixed transform of token digests into a unit vector. It is reproducible and server-light, which suits a frozen baseline. It does not learn synonymy; nearby vectors mainly reflect shared hashed token mass.

### Figure caption
**Figure C.** Hash-v1 query/document embedding used by AssistIQ Baseline A (\(d=384\), SHA-256 accumulation, L2 normalisation).

---

## FIGURE D — Knowledge Retrieval + Confidence

### Figure title
**Figure D.** Published-chunk retrieval (\(k=3\)) and top-score confidence heuristic.

### Flowchart

```mermaid
flowchart TD
  A([Query embedding e]) --> B[Chroma HNSW<br/>cosine distance]
  B --> C[Filter: status = published]
  C --> D["Retrieve top-k, k = 3"]
  D --> E["s_i = max(0, 1 − d_i)"]
  E --> F[Order by s_i]
  F --> G[Validate chunks in PostgreSQL]
  G --> H[Citations + s_top = first score]
  H --> I{citations empty<br/>or s_top missing?}
  I -->|Yes| N[NO_EVIDENCE]
  I -->|No| J{"s_top ≥ 0.65?"}
  J -->|Yes| HIG[HIGH_CONFIDENCE]
  J -->|No| K{"s_top ≥ 0.35?"}
  K -->|Yes| LOW[LOW_CONFIDENCE]
  K -->|No| N
  N --> W{knowledge / general intent?}
  W -->|Yes| X[Append grounding warning]
  W -->|No| Y([Confidence label C])
  HIG --> Y
  LOW --> Y
  X --> Y

  classDef decision fill:#E8F1F8,stroke:#1F4E79
  classDef math fill:#DEEBF7,stroke:#1F4E79
  classDef process fill:#F5F7FA,stroke:#44546A
  class I,J,K,W decision
  class E,D math
  class B,C,F,G,H,X process
```

### Mathematical representation

\[
s_i=\max(0,1-d_i),\qquad
\mathcal{C}=\mathrm{TopK}(\{s_i\},k=3),\qquad
s_{\mathrm{top}}=s_{(1)}.
\]

\[
C(x)=\begin{cases}
\texttt{HIGH\_CONFIDENCE}, & s_{\mathrm{top}}\ge 0.65\ \wedge\ |\mathcal{C}|\ge 1,\\
\texttt{LOW\_CONFIDENCE}, & 0.35\le s_{\mathrm{top}}<0.65,\\
\texttt{NO\_EVIDENCE}, & \text{otherwise.}
\end{cases}
\]

Confidence uses **\(s_{\mathrm{top}}\)** (first citation), not the mean of all scores. Low retrieval confidence does **not** auto-escalate in Baseline A.

### Short explanation
Retrieval grounds later generation in published knowledge only. The confidence label is a threshold heuristic on the best hit, intended as an operational signal of thin evidence rather than a calibrated probability of answer correctness.

### Figure caption
**Figure D.** AssistIQ knowledge retrieval (\(k=3\), cosine HNSW, published filter) and top-citation confidence thresholds (0.65 / 0.35).

---

## FIGURE E — RAG Response Generation

### Figure title
**Figure E.** Retrieval-augmented prompt construction and generation.

### Flowchart

```mermaid
flowchart TD
  A([User question]) --> P[Assemble RAG prompt]
  H[History: last 6 turns<br/>≤400 chars each] --> P
  K[KB citations: ≤5 blocks<br/>≤500 chars each] --> P
  T[Ticket context if any<br/>≤5 tickets] --> P
  P --> D[Mark retrieved text as DATA<br/>question as QUESTION]
  D --> M[Selected generation LLM]
  M --> G[Generate answer]
  G --> C[Citation validation<br/>keep doc+chunk ids]
  C --> F[Confidence check]
  F --> R([Final response])

  classDef process fill:#F5F7FA,stroke:#44546A
  classDef math fill:#DEEBF7,stroke:#1F4E79
  class P,D,M,G,C,F process
  class H,K,T math
```

### Mathematical representation

Prompt composition (Baseline A limits):

\[
\mathrm{Prompt}=(\mathrm{System}_{\mathrm{DATA\text{-}only}},\, H_{1:6}^{\le 400},\, \{[KB\text{-}n]\}_{n\le 5}^{\le 500},\, Q).
\]

Generation uses an external LLM; AssistIQ does not train that model. Citation checks are structural; they do not prove entailment of every sentence.

### Short explanation
RAG separates untrusted retrieved passages from system instructions so document text cannot easily override control rules. The model answers from DATA plus the question. This reduces one failure mode (prompt injection from KB text) but does not eliminate hallucination or guarantee factual correctness.

### Figure caption
**Figure E.** AssistIQ RAG generation path: constrained prompt, registry LLM, citation scrubbing, and confidence labelling.

---

## FIGURE F — IT / Software Access Decision Algorithm

### Figure title
**Figure F.** Rule-based IT request policy with mock execution.

### Flowchart

```mermaid
flowchart TD
  A([Software / access request]) --> B[Entity extraction]
  B --> C[Catalog match<br/>longest alias substring]
  C --> D["confidence = 0.9 if matched<br/>else 0.35; PERMISSION ≤ 0.6"]
  D --> E{Critical keywords?}
  E -->|Yes| ESC[ESCALATE]
  E -->|No| F{PERMISSION or<br/>privileged keywords?}
  F -->|Yes| ESC
  F -->|No| G{Catalog matched?}
  G -->|No| DENY[DENY]
  G -->|Yes| H{Catalog enabled?}
  H -->|No| DENY
  H -->|Yes| I{Catalog risk CRITICAL?}
  I -->|Yes| ESC
  I -->|No| J{HIGH risk or<br/>approval_required?}
  J -->|Yes| APR[APPROVAL_REQUIRED]
  J -->|No| K{MEDIUM risk?}
  K -->|Yes| APR
  K -->|No| ALL[ALLOW low risk]
  ALL --> M[Mock execution]
  APR --> N[Wait for approval<br/>then mock if approved]
  ESC --> O([Human review])
  DENY --> P([Rejected])
  M --> Q([Simulated result])

  NOTE[Mock execution only — no real install / access grant]

  classDef decision fill:#E8F1F8,stroke:#1F4E79
  classDef warn fill:#FCE4D6,stroke:#C65911
  classDef process fill:#F5F7FA,stroke:#44546A
  class E,F,G,H,I,J,K decision
  class M,NOTE warn
  class B,C,D process
```

### Mathematical representation

Extraction confidence (verified):

\[
\mathrm{conf}=\begin{cases}
0.9,& \text{catalog matched},\\
0.35,& \text{otherwise},
\end{cases}
\qquad
\mathrm{conf}\leftarrow\min(\mathrm{conf},0.6)\ \text{if type = PERMISSION}.
\]

Policy order: critical language → escalate; permission/privileged → escalate; no catalog → deny; disabled → deny; catalog CRITICAL → escalate; HIGH or `approval_required` → approval; MEDIUM → approval; else ALLOW (LOW) → mock execute.

### Short explanation
IT automation is intentionally non-generative at the decision layer. Catalog and keyword rules decide allow, deny, escalate, or approval. Terminal “success” in Baseline A is produced by `MockExecutionAdapter` and must not be read as a real install or entitlement change.

### Figure caption
**Figure F.** AssistIQ IT/software-access decision algorithm (rule hierarchy and mock execution).

---

## FIGURE G — Password Reset Decision Algorithm

### Figure title
**Figure G.** Password-reset verification, risk, policy, confirmation, and mock IAM.

### Flowchart

```mermaid
flowchart TD
  A([Password reset request]) --> B[Create request<br/>TTL = 30 minutes]
  B --> V[Identity verification]
  V --> V1{Submitted email<br/>= actor email?}
  V1 -->|No| VF[FAILED<br/>or escalate if cross-user staff path]
  V1 -->|Yes| V2{Suspicious claims<br/>in message?}
  V2 -->|Yes| VE[REQUIRES_ESCALATION]
  V2 -->|No| OK[VERIFIED]
  VF --> R[Risk assessment]
  VE --> R
  OK --> R
  R --> R2[Employee self → often LOW<br/>suspicious / failed / other-user / privileged target → HIGH/CRITICAL]
  R2 --> P[Policy evaluation]
  P --> P1{Employee resets<br/>another user?}
  P1 -->|Yes| DENY[DENY]
  P1 -->|No| P2{FAILED and<br/>risk HIGH/CRITICAL?}
  P2 -->|Yes| ESC[ESCALATE]
  P2 -->|No| P3{FAILED?}
  P3 -->|Yes| DENY
  P3 -->|No| P4{Not VERIFIED?}
  P4 -->|Yes| ESC
  P4 -->|No| P5{Risk HIGH/CRITICAL?}
  P5 -->|Yes| ESC
  P5 -->|No| CONF[REQUIRE_CONFIRMATION]
  CONF --> C[Explicit confirmation]
  C --> M[Mock IAM]
  M --> Z([Simulated reset only])

  NOTE[Mock IAM only — no live password change]

  classDef decision fill:#E8F1F8,stroke:#1F4E79
  classDef warn fill:#FCE4D6,stroke:#C65911
  classDef process fill:#F5F7FA,stroke:#44546A
  class V1,V2,P1,P2,P3,P4,P5 decision
  class M,NOTE,Z warn
  class B,V,R,R2,P,C process
```

### Mathematical representation

Let \(e_s\) be submitted email, \(e_a\) actor email, \(v\) verification status, \(\rho\) risk level. After verification and risk assessment, policy follows (simplified from implementation order):

\[
\pi=
\begin{cases}
\texttt{DENY}, & \text{employee targets other user},\\
\texttt{ESCALATE}, & v=\texttt{FAILED}\wedge \rho\in\{\texttt{HIGH},\texttt{CRITICAL}\},\\
\texttt{DENY}, & v=\texttt{FAILED}\text{ otherwise},\\
\texttt{ESCALATE}, & v\neq\texttt{VERIFIED},\\
\texttt{ESCALATE}, & \rho\in\{\texttt{HIGH},\texttt{CRITICAL}\},\\
\texttt{REQUIRE\_CONFIRMATION}, & \text{otherwise}.
\end{cases}
\]

Expiry: request TTL \(=30\) minutes. Confirmation precedes mock IAM; no live password write occurs.

### Short explanation
Password handling keeps identity and risk decisions outside the LLM. Session email matching, risk rules, and policy gates precede any simulated reset. The thirty-minute TTL bounds abandoned requests. Mock IAM makes the academic prototype safe to demonstrate without changing real credentials.

### Figure caption
**Figure G.** AssistIQ password-reset decision algorithm (verify → risk → policy → confirm → mock IAM; TTL = 30 min).

---

## Consistency checklist

| Check | Status |
|-------|--------|
| Intent uses ordered substring keywords + “?” fallback | Matches `detect_intent.py` |
| Optional lightweight override only for `knowledge_query` | Matches |
| Routing map values | Matches `intents.py` |
| hash-v1 / \(d=384\) / SHA-256 / L2 | Matches `embedding_service.py` |
| \(k=3\), \(s=\max(0,1-d)\), confidence on **top** score | Matches retrieval + `confidence_check.py` |
| NO_EVIDENCE warning; no auto-escalate from RAG confidence | Matches |
| IT policy order + mock execution | Matches `policy_service.py` / mock adapter |
| Password TTL 30 min; mock IAM; policy hierarchy | Matches password services |
| No SVM/BERT/BM25/hybrid/real install/live password | Not claimed |

---

*Application source code was not modified. These figures are methodology artefacts for the research paper.*
