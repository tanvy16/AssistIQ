# AssistIQ — Literature Verification Matrix (Review 2)

**Project:** AssistIQ — AI-Enabled Intelligent IT Service Management Platform  
**Purpose:** Manual Google Scholar verification support for Review 2 literature survey  
**Verification date:** 21 August 2026 (Papers 1–10); 23 August 2026 (Papers 11–12)  
**Verification method:** Web search against publisher pages, DOI resolvers, arXiv, AISeL, ScholarSpace, and journal sites. Papers 11–12 were first retrieved from [Consensus](https://consensus.app/search/how-effective-is-retrieval-augmented-generation-fo/MF52dg2VRmKs5zIQyYDfJw/) and then confirmed on Google Scholar plus ACM Digital Library.

---

## Verification Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Bibliographic details confirmed from authoritative source |
| ⚠️ | Title/venue confirmed; verify author spelling or full author list manually |
| 📄 | Preprint — peer-review status should be noted in citation |

---

## Summary Table (12 Papers)

| # | Paper | Year | Venue | DOI / URL | Verification |
|---|-------|------|-------|-----------|--------------|
| 1 | Improving Support Ticket Systems Using Machine Learning: A Literature Review | 2022 | HICSS-55 | [10.24251/HICSS.2022.238](https://doi.org/10.24251/hicss.2022.238) | ✅ |
| 2 | Automated Ticket Classification for Information Technology Helpdesks using Machine Learning | 2023 | IEEE ZCICT 2023 | [10.1109/ZCICT59466.2023.10528578](https://doi.org/10.1109/zcict59466.2023.10528578) | ⚠️ |
| 3 | Incident and Problem Ticket Clustering and Classification Using Deep Learning | 2023 | ZTE Communications 21(4) | [Journal page](https://zte.magtechjournal.com/EN/Y2023/V21/I4/69) | ✅ |
| 4 | Machine Learning for Classification of IT Support Tickets | 2023 | IEEE CYMAEN 2023 | [10.1109/cymaen57228.2023.10051041](https://doi.org/10.1109/cymaen57228.2023.10051041) | ✅ |
| 5 | Generative Assistants for Handling Incidents in IT Service Management | 2024 | ICIS 2024 Proceedings | [AISeL](https://aisel.aisnet.org/icis2024/digtech_fow/digtech_fow/19/) | ✅ |
| 6 | LLMRAG: An Optimized Digital Support Service using LLM and Retrieval-Augmented Generation | 2024 | IEEE FMEC 2024 | [10.1109/fmec62297.2024.10710181](https://doi.org/10.1109/fmec62297.2024.10710181) | ✅ |
| 7 | Retrieval Augmented Generation-Based Incident Resolution Recommendation System for IT Support | 2024 | arXiv preprint | [10.48550/arXiv.2409.13707](https://arxiv.org/abs/2409.13707) | 📄 ✅ |
| 8 | InspectorRAGet: An Introspection Platform for RAG Evaluation | 2024 | arXiv preprint | [10.48550/arXiv.2404.17347](https://arxiv.org/abs/2404.17347) | 📄 ✅ |
| 9 | Utilizing Large Language Models for Automating Technical Customer Support | 2024 | arXiv preprint | [10.48550/arXiv.2406.01407](https://arxiv.org/abs/2406.01407) | 📄 ✅ |
| 10 | Agentic Automation and Work Flow Orchestration in Enterprise SaaS: Effects on Ticket Resolution Time and Employee Productivity in IT Service Management | 2024 | IJSAT 15(4) | [10.71097/ijsat.v15.i4.9876](https://doi.org/10.71097/ijsat.v15.i4.9876) | ✅ |
| 11 | Retrieval-Augmented Generation with Knowledge Graphs for Customer Service Question Answering | 2024 | ACM SIGIR 2024 | [10.1145/3626772.3661370](https://doi.org/10.1145/3626772.3661370) | ✅ |
| 12 | Optimizing and Evaluating Enterprise Retrieval-Augmented Generation (RAG): A Content Design Perspective | 2024 | ACM ICAAI 2024 | [10.1145/3704137.3704181](https://doi.org/10.1145/3704137.3704181) | ✅ |

---

## Detailed Matrix

### Paper 1

| Field | Details |
|-------|---------|
| **Paper** | Improving Support Ticket Systems Using Machine Learning: A Literature Review |
| **Authors** | Simon Fuchs, Clemens Drieschner, Holger Wittges (Technical University of Munich) |
| **Year** | 2022 |
| **Venue** | Proceedings of the 55th Hawaii International Conference on System Sciences (HICSS-55) |
| **DOI** | 10.24251/HICSS.2022.238 |
| **Official URL** | https://doi.org/10.24251/hicss.2022.238 ; https://aisel.aisnet.org/hicss-55/da/service_analytics/6/ |
| **Google Scholar verification** | ✅ Verified via DOI resolver and AISeL/HICSS proceedings |
| **Problem Statement** | Manual support ticket distribution is costly, slow, and reduces customer satisfaction; organizations need a consolidated view of ML automation for support ticket systems (STSs). |
| **Methodology** | Narrative literature review across Scopus, IEEE Xplore, Ebsco, and Web of Science (English, February 2021 search window). |
| **Dataset / Experimental Setup** | Review of prior empirical studies (not a new primary dataset); synthesis of reported algorithm comparisons from included papers. |
| **Key Results** | Incident management automation is the dominant research topic; SVM is the most frequently used classifier (10 papers) and best-performing in 6 papers (reported accuracies 63%–98%, commonly ~80%–90%); Random Forest second most used (7 papers). |
| **Brief Discussion** | Provides a field-level map of ML-for-ticketing research and identifies gaps in escalation prediction and sentiment analysis. |
| **Limitations** | Review methodology depends on search terms and database coverage; reported accuracies are not directly comparable across heterogeneous datasets. |
| **Relevance to AssistIQ** | Justifies ticket classification as a lightweight-ML candidate in Phase 5 and confirms that structured ticket metadata/text is a viable automation input in AssistIQ’s ticketing module. |

---

### Paper 2

| Field | Details |
|-------|---------|
| **Paper** | Automated Ticket Classification for Information Technology Helpdesks using Machine Learning |
| **Authors** | P. Dlodlo, T. Sibanda ⚠️ *(confirm full names on IEEE Xplore)* |
| **Year** | 2023 |
| **Venue** | 2023 2nd Zimbabwe Conference of Information and Communication Technologies (ZCICT), IEEE |
| **DOI** | 10.1109/ZCICT59466.2023.10528578 |
| **Official URL** | https://ieeexplore.ieee.org/document/10528578 |
| **Google Scholar verification** | ⚠️ DOI and abstract verified; IEEE Xplore author metadata should be confirmed manually |
| **Problem Statement** | Manual IT helpdesk ticket classification is time-consuming, error-prone, and increases resolution time. |
| **Methodology** | Hyperparameter tuning with GridSearchCV, RandomizedSearchCV, and K-Fold cross-validation on KNN, SVM, and Random Forest; under-sampling for class imbalance. |
| **Dataset / Experimental Setup** | IT helpdesk ticket dataset (paper describes as unbalanced; balancing applied). |
| **Key Results** | Tuned SVM achieved **94.6% accuracy**, outperforming tuned KNN and base models; hyperparameter tuning reduced Random Forest accuracy. |
| **Brief Discussion** | Demonstrates that classical ML with careful tuning can reach high classification accuracy for IT ticket routing. |
| **Limitations** | Single dataset and conference-scale evaluation; class-balancing strategy may discard useful minority-class examples. |
| **Relevance to AssistIQ** | Supports Phase 5 lightweight ML for ticket category/priority routing using AssistIQ’s existing ticket categories (`network`, `access`, `hardware`, `software`, `other`). |

---

### Paper 3

| Field | Details |
|-------|---------|
| **Paper** | Incident and Problem Ticket Clustering and Classification Using Deep Learning |
| **Authors** | Feng Hailin, Han Jing, Huang Leijun, Sheng Ziwei, Gong Zican |
| **Year** | 2023 |
| **Venue** | ZTE Communications, Vol. 21, No. 4, pp. 69–77 |
| **DOI / URL** | https://zte.magtechjournal.com/EN/Y2023/V21/I4/69 |
| **Google Scholar verification** | ✅ Verified via journal publication page |
| **Problem Statement** | Cloud production environments generate large volumes of incident/problem tickets requiring better clustering and routing to dispatch departments. |
| **Methodology** | PCA, K-means, LDA for clustering; pre-trained BERT for ticket classification to dispatch department; domain-knowledge preprocessing. |
| **Dataset / Experimental Setup** | Real production cloud service ticket data (enterprise environment). |
| **Key Results** | Classification model achieved **86% accuracy** for dispatch-department prediction; domain-specific preprocessing was critical. |
| **Brief Discussion** | Shows deep learning (transformer-based) gains over bag-of-words approaches when domain preprocessing is applied. |
| **Limitations** | Enterprise-specific vocabulary and infrastructure; results may not transfer without retraining and domain adaptation. |
| **Relevance to AssistIQ** | Informs Phase 5 deep-learning path for semantic ticket routing and Phase 4 chunk preprocessing quality. |

---

### Paper 4

| Field | Details |
|-------|---------|
| **Paper** | Machine Learning for Classification of IT Support Tickets |
| **Authors** | Leonardo Santiago Benitez Pereira, Robinson Pizzio, Samir Bonho, Leonardo Mozzer Ferraz De Souza, Antonio Carlos Arnoni |
| **Year** | 2023 |
| **Venue** | 2023 IEEE CYMAEN, IEEE |
| **DOI** | 10.1109/cymaen57228.2023.10051041 |
| **Official URL** | https://doi.org/10.1109/cymaen57228.2023.10051041 |
| **Google Scholar verification** | ✅ Verified via DOI resolver |
| **Problem Statement** | Helpdesk teams must quickly associate incoming tickets with correct topics to reduce resolution time. |
| **Methodology** | Supervised ML classification model; deployed web prototype (backend + frontend) for analyst use. |
| **Dataset / Experimental Setup** | Anonymized IT support ticket dataset (7 categories); code/model/data released for reproduction. |
| **Key Results** | **75% average precision** across 7 categories; operational prototype delivered. |
| **Brief Discussion** | Links research classification models to practical helpdesk tooling — aligned with AssistIQ’s full-stack approach. |
| **Limitations** | Moderate precision; multi-class imbalance and production drift not deeply evaluated. |
| **Relevance to AssistIQ** | Validates end-to-end ML ticket classification integrated with a web application, mirroring AssistIQ’s FastAPI + React architecture. |

---

### Paper 5

| Field | Details |
|-------|---------|
| **Paper** | Generative Assistants for Handling Incidents in IT Service Management |
| **Authors** | Rainer Schmidt, Rainer Alt, Alfred Zimmermann |
| **Year** | 2024 |
| **Venue** | ICIS 2024 Proceedings (Digital Technologies and the Future of Work track) |
| **DOI / URL** | https://aisel.aisnet.org/icis2024/digtech_fow/digtech_fow/19/ |
| **Google Scholar verification** | ✅ Verified via AISeL ICIS proceedings |
| **Problem Statement** | ITSM incident handling suffers from high escalation rates and inefficient retrieval of IT documentation during incidents. |
| **Methodology** | Design Science Research (DSR); RAG + vector database artifact; quantitative evaluation of escalation, self-service resolution, first-contact resolution, and average resolution time. |
| **Dataset / Experimental Setup** | Preliminary testing with Microsoft Knowledge Base documentation for retrieval accuracy. |
| **Key Results** | **90.91% accuracy** in identifying relevant documentation in preliminary KB testing (full operational metrics reported as evaluation framework, not final production deployment). |
| **Brief Discussion** | Directly connects RAG and vector retrieval to ITSM incident management — closest academic analog to AssistIQ Phases 4 and 6. |
| **Limitations** | Short paper; preliminary KB test rather than full enterprise deployment; generative answer quality not fully benchmarked. |
| **Relevance to AssistIQ** | Strong justification for AssistIQ’s Neon metadata + Chroma vector split and future RAG chatbot with citations. |

---

### Paper 6

| Field | Details |
|-------|---------|
| **Paper** | LLMRAG: An Optimized Digital Support Service using LLM and Retrieval-Augmented Generation |
| **Authors** | Oscar Cederlund, Sadi Alawadi, Feras M. Awaysheh |
| **Year** | 2024 |
| **Venue** | 2024 9th International Conference on Fog and Mobile Edge Computing (FMEC), IEEE |
| **DOI** | 10.1109/fmec62297.2024.10710181 |
| **Official URL** | https://doi.org/10.1109/fmec62297.2024.10710181 |
| **Google Scholar verification** | ✅ Verified via DOI/OpenAIRE metadata |
| **Problem Statement** | IT service desk technicians need automated solution suggestions for incoming tickets without replacing human judgment. |
| **Methodology** | LLM + RAG integration in real-world service desk; two-week controlled evaluation with technician feedback and solution retention analysis. |
| **Dataset / Experimental Setup** | Real-world IT service desk ticket stream (Swedish language context noted as challenge). |
| **Key Results** | **38.4%** of generated solutions were retained by technicians; integration, unstructured data, and language adaptation identified as key challenges. |
| **Brief Discussion** | Shows practical partial adoption of LLM-RAG in production support — human retention rate is a meaningful operational metric. |
| **Limitations** | Short evaluation window; mixed technician opinions; language/domain specificity. |
| **Relevance to AssistIQ** | Informs Phase 6 human-in-the-loop design and Phase 9 evaluation metrics (retention/groundedness, not just retrieval score). |

---

### Paper 7

| Field | Details |
|-------|---------|
| **Paper** | Retrieval Augmented Generation-Based Incident Resolution Recommendation System for IT Support |
| **Authors** | Paulina Toro Isaza, Michael Nidd, Noah Zheutlin, Jae-wook Ahn, Chidansh Amitkumar Bhatt, Yu Deng, Ruchi Mahindru, Martin Franz, Hans Florian, Salim Roukos (IBM Research) |
| **Year** | 2024 |
| **Venue** | arXiv preprint (cs.CL) |
| **DOI** | 10.48550/arXiv.2409.13707 |
| **Official URL** | https://arxiv.org/abs/2409.13707 |
| **Google Scholar verification** | 📄 ✅ Verified via arXiv |
| **Problem Statement** | IT support/AIOps domains lack public datasets and domain-tuned generative models; clients may avoid large proprietary LLMs due to cost/privacy. |
| **Methodology** | Multi-stage pipeline: encoder-only classifier (IBM Slate 125m fine-tuned on ~14,000 SME-labeled examples) for single-turn case detection; RAG for grounded solution recommendation; LLM for query generation. |
| **Dataset / Experimental Setup** | Client IT product support tickets; official support documents as grounding corpus. |
| **Key Results** | Reports substantial retrieval improvement with re-ranking (IBM Slate 125m retriever); preliminary validations and deployment plans described — **no single headline accuracy figure for end-to-end resolution** in abstract. |
| **Brief Discussion** | Demonstrates hybrid architecture (classifier + RAG + LLM) matching AssistIQ’s proposed multi-model design. |
| **Limitations** | Preprint; limited public IT-support benchmarks; client-specific domain. |
| **Relevance to AssistIQ** | Blueprint for Phase 5 model routing (encoder for classification, LLM only when needed) and Phase 4/6 RAG grounding requirements. |

---

### Paper 8

| Field | Details |
|-------|---------|
| **Paper** | InspectorRAGet: An Introspection Platform for RAG Evaluation |
| **Authors** | Kshitij Fadnis, Siva Sankalp Patel, Odellia Boni, Yannis Katsis, Sara Rosenthal, Benjamin Sznajder, Marina Danilevsky (IBM Research) |
| **Year** | 2024 |
| **Venue** | arXiv preprint |
| **DOI** | 10.48550/arXiv.2404.17347 |
| **Official URL** | https://arxiv.org/abs/2404.17347 |
| **Google Scholar verification** | 📄 ✅ Verified via arXiv |
| **Problem Statement** | RAG evaluation often stops at aggregate automatic metrics; developers lack tools for instance-level error analysis and annotator quality assessment. |
| **Methodology** | Platform design for holistic RAG evaluation lifecycle: aggregate metrics, instance inspection, human + algorithmic judges, annotator behavior analysis. |
| **Dataset / Experimental Setup** | Demonstrated on existing and new RAG evaluation datasets (platform use cases described in paper). |
| **Key Results** | Platform enables actionable instance-level insights beyond aggregate scores; publicly released at https://github.com/IBM/InspectorRAGet |
| **Brief Discussion** | Supports the need for Phase 9 observability beyond simple retrieval hit rate. |
| **Limitations** | Tooling paper; does not define production SLA thresholds for enterprise ITSM. |
| **Relevance to AssistIQ** | Directly supports Phase 9 RAG evaluation (faithfulness, context precision/recall, instance-level debugging). |

---

### Paper 9

| Field | Details |
|-------|---------|
| **Paper** | Utilizing Large Language Models for Automating Technical Customer Support |
| **Authors** | Jochen Wulf, Jürg Meierhofer (Zurich University of Applied Sciences) |
| **Year** | 2024 |
| **Venue** | arXiv preprint |
| **DOI** | 10.48550/arXiv.2406.01407 |
| **Official URL** | https://arxiv.org/abs/2406.01407 |
| **Google Scholar verification** | 📄 ✅ Verified via arXiv |
| **Problem Statement** | Technical customer support (TCS) faces skills shortages and information overload; LLM applicability and organizational data-sharing constraints are not fully understood. |
| **Methodology** | Prototype development and data analysis for LLM-based text correction, inquiry summarization, and question answering in TCS workflows. |
| **Dataset / Experimental Setup** | Real customer data through organizational prototypes (details in paper). |
| **Key Results** | Promising efficiency/quality improvements reported qualitatively; emphasizes need for **quality-assured implementation** and **organizational/data ecosystem adjustments** — quantitative benchmark table not emphasized in abstract. |
| **Brief Discussion** | Highlights that LLM deployment is socio-technical, not purely algorithmic. |
| **Limitations** | Preprint; limited generalizable quantitative benchmarks in abstract; data privacy constraints. |
| **Relevance to AssistIQ** | Supports AssistIQ’s decision not to use LLM for every task (Phases 4–5) and Phase 10 governance requirements. |

---

### Paper 10

| Field | Details |
|-------|---------|
| **Paper** | Agentic Automation and Work Flow Orchestration in Enterprise SaaS: Effects on Ticket Resolution Time and Employee Productivity in IT Service Management |
| **Authors** | Sri Hari Deep Kolagani |
| **Year** | 2024 |
| **Venue** | International Journal of Science and Advanced Technology (IJSAT), Vol. 15, Issue 4 |
| **DOI** | 10.71097/ijsat.v15.i4.9876 |
| **Official URL** | https://www.ijsat.org/research-paper.php?id=9876 |
| **Google Scholar verification** | ✅ Verified via IJSAT publication page |
| **Problem Statement** | Can AI autonomous agents improve ITSM ticket resolution time, first-contact resolution (FCR), and agent productivity versus manual workflows? |
| **Methodology** | Quasi-experimental comparison using retrospective datasets (HuggingFace, Kaggle) comparing agent-aided vs manual workflows. |
| **Dataset / Experimental Setup** | Public retrospective ITSM-style datasets (not live enterprise deployment). |
| **Key Results** | Reports up to **13 hours saved per ticket**, **53% FCR increase**, and **22% agent productivity increase** vs manual baseline (paper abstract). |
| **Brief Discussion** | Supports agentic workflow motivation for Phases 7–8 but uses secondary datasets — enterprise validation still required. |
| **Limitations** | Quasi-experimental design; public dataset may not reflect enterprise SLA complexity; single-author journal article. |
| **Relevance to AssistIQ** | Motivates LangGraph workflow orchestration (Phase 7) with measurable ITSM KPIs (resolution time, FCR, SLA compliance). |

---

### Paper 11

| Field | Details |
|-------|---------|
| **Paper** | Retrieval-Augmented Generation with Knowledge Graphs for Customer Service Question Answering |
| **Authors** | Zhentao Xu, Mark Jerome Cruz, Matthew Guevara, Tie Wang, Manasi Deshpande, Xiaofeng Wang, Zheng Li (LinkedIn) |
| **Year** | 2024 |
| **Venue** | Proceedings of the 47th International ACM SIGIR Conference on Research and Development in Information Retrieval (SIGIR ’24), pp. 2905–2909 |
| **DOI** | 10.1145/3626772.3661370 |
| **Official URL** | https://doi.org/10.1145/3626772.3661370 ; https://arxiv.org/abs/2404.17723 |
| **Consensus source** | ✅ Retrieved from Consensus search: *“How effective is retrieval-augmented generation for IT service desk ticket resolution and knowledge-grounded support?”* (Xu 2024) |
| **Google Scholar verification** | ✅ Verified 23 August 2026: first result for the exact title + “Xu 2024”; ACM PDF; **Cited by 370**; [Scholar query](https://scholar.google.com/scholar?q=Retrieval-Augmented+Generation+with+Knowledge+Graphs+for+Customer+Service+Question+Answering+Xu+2024) |
| **Problem Statement** | Conventional RAG treats historical issue tickets as plain text chunks, losing intra-ticket structure (summary vs. steps-to-reproduce vs. solution) and inter-ticket relations (clone / caused-by / related-to). |
| **Methodology** | Dual-level knowledge graph: intra-ticket trees (rule + LLM parse) and inter-ticket explicit/implicit edges; E5 embeddings stored in a vector DB (Qdrant); query entity/intent parse; subgraph retrieval; GPT-4 generation with text-EBR fallback. |
| **Dataset / Experimental Setup** | Curated golden set of typical queries, tickets, and authoritative solutions; same GPT-4 + E5 models for KG-RAG vs. text-chunk EBR baseline; six-month A/B deployment in LinkedIn customer service. |
| **Key Results** | Retrieval: MRR **0.927 vs 0.522** (+77.6%), Recall@1 **0.860 vs 0.400**, NDCG@1 **0.860 vs 0.400**. Generation: BLEU **0.377 vs 0.057**, METEOR **0.613 vs 0.279**, ROUGE **0.546 vs 0.183**. Production: median resolution time **−28.6%** (P50 7h → 5h; mean 40h → 15h). |
| **Brief Discussion** | Strong production evidence that structure-preserving retrieval beats naive chunking for support tickets — complementary to AssistIQ’s current document-chunk pipeline. |
| **Limitations** | Industry short paper; LinkedIn-specific ticket schema and KG template; golden-set size not fully disclosed; GPT-4 dependency. |
| **Relevance to AssistIQ** | Informs Phase 4 chunking/section integrity, Phase 6 grounded ticket QA, and Phase 9 retrieval metrics (MRR, Recall@k, NDCG@k, resolution-time KPI). |

---

### Paper 12

| Field | Details |
|-------|---------|
| **Paper** | Optimizing and Evaluating Enterprise Retrieval-Augmented Generation (RAG): A Content Design Perspective |
| **Authors** | Sarah Packowski, Inge Halilovic, Jenifer Schlotfeldt, Trish Smith (IBM) |
| **Year** | 2024 |
| **Venue** | Proceedings of the 8th International Conference on Advances in Artificial Intelligence (ICAAI 2024), London, 17–19 October 2024, pp. 162–167, ACM |
| **DOI** | 10.1145/3704137.3704181 |
| **Official URL** | https://doi.org/10.1145/3704137.3704181 ; https://arxiv.org/abs/2410.12812 |
| **Consensus source** | ✅ Retrieved from Consensus search (Packowski 2024; result #2 on the same RAG/IT-support query) |
| **Google Scholar verification** | ✅ Verified 23 August 2026: first result for the exact title + “Packowski 2024”; ACM PDF; **Cited by 26**; 3 versions; [Scholar query](https://scholar.google.com/scholar?q=%22Optimizing+and+Evaluating+Enterprise+Retrieval-Augmented+Generation%22+Packowski+2024) |
| **Problem Statement** | Enterprise RAG over product documentation does not behave like Wikipedia-benchmark RAG; model-centric papers under-emphasize knowledge-base writing quality and human evaluation of novel user questions. |
| **Methodology** | Practice-based report of modular, model-agnostic RAG (search + LLM as closed-box APIs); question-driven content strategy; whole-topic (“small2big”) grounding; human-in-the-lead evaluation web app (valid question / class / article exists / search success / good answer). |
| **Dataset / Experimental Setup** | 189 Natural Questions items (Earth subset) for a content-rewrite experiment; production product-documentation RAG with July–December operational evaluation of real user questions. |
| **Key Results** | Minor KB text edits raised the NQ experiment to **100%** correct answers. Production: topic coverage for valid questions improved from **40% missing content (July)** to **75% coverage (December)**; search then failed to find the relevant topic **47%** of the time — evaluation localized the next fix. Natural-language questions rose from 25% to 39% of search queries. |
| **Brief Discussion** | Retrieval success is a content-and-search problem, not only a model problem; citations, whole-topic retrieval, and human review are first-class design choices. |
| **Limitations** | Experience report rather than a controlled multi-org experiment; search/LLM internals are closed boxes; user feedback rate <1%. |
| **Relevance to AssistIQ** | Justifies Phase 4 published-document quality, citation links, and parent-chunk retrieval; aligns Phase 9 with human-in-the-lead metrics rather than BLEU/ROUGE-only scoring. |

---

## Cross-Paper Consensus Notes (for report synthesis)

| Theme | Consensus supported by multiple papers | Persistent gap |
|-------|----------------------------------------|----------------|
| Ticket classification | Classical ML (SVM, RF) and DL (BERT) both effective with domain preprocessing (Papers 1–4) | Dataset heterogeneity limits cross-org generalization |
| RAG in ITSM | RAG improves documentation retrieval and grounded support recommendations (Papers 5–7, 11–12) | Limited public IT-support benchmarks; privacy/cost constrain large LLM use |
| Structured vs naive retrieval | Ticket/document structure and KB writing quality can outperform model-only tuning (Papers 11–12) | Graph/template construction is org-specific |
| LLM limitations | LLM value requires quality assurance, data governance, and human oversight (Papers 6, 9, 12) | Organizational and integration barriers under-studied |
| Workflow automation | Agentic/automated workflows can improve FCR and productivity (Paper 10) | Longitudinal enterprise evidence still sparse |
| Evaluation | Aggregate metrics insufficient; instance-level and human-in-the-lead RAG analysis needed (Papers 8, 12) | Standardized ITSM+RAG evaluation suites missing |

---

## Manual Verification Checklist (for examiner)

- [ ] Paper 1 — Google Scholar: `"Improving Support Ticket Systems Using Machine Learning" Fuchs 2022`
- [ ] Paper 2 — Google Scholar: `"Automated Ticket Classification" Dlodlo Sibanda 2023`
- [ ] Paper 3 — Google Scholar: `"Incident and Problem Ticket Clustering" Feng 2023`
- [ ] Paper 4 — Google Scholar: `"Machine Learning for Classification of IT Support Tickets" Benitez Pereira 2023`
- [ ] Paper 5 — Google Scholar: `"Generative Assistants for Handling Incidents" Schmidt ICIS 2024`
- [ ] Paper 6 — Google Scholar: `"LLMRAG" Cederlund 2024`
- [ ] Paper 7 — Google Scholar: `arXiv:2409.13707 Toro Isaza`
- [ ] Paper 8 — Google Scholar: `arXiv:2404.17347 InspectorRAGet`
- [ ] Paper 9 — Google Scholar: `arXiv:2406.01407 Wulf Meierhofer`
- [ ] Paper 10 — Google Scholar: `Kolagani agentic automation ITSM 2024`
- [x] Paper 11 — Google Scholar: `"Retrieval-Augmented Generation with Knowledge Graphs for Customer Service Question Answering" Xu 2024` — verified 23 Aug 2026 (Cited by 370; ACM PDF)
- [x] Paper 12 — Google Scholar: `"Optimizing and Evaluating Enterprise Retrieval-Augmented Generation" Packowski 2024` — verified 23 Aug 2026 (Cited by 26; ACM PDF; 3 versions)
