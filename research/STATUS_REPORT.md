# AssistIQ Research Evaluation — Status Report

## What was tested (executed)

| Experiment | Status | Evidence |
|------------|--------|----------|
| A Intent classification (keyword vs SVM/LR/RF) | **MEASURED** | `research/results/classification/` |
| B Routing (map vs direct SVM vs oracle) | **MEASURED** | `research/results/routing/` |
| C Retrieval (hash-v1 vs BM25 vs TF–IDF) | **MEASURED** | `research/results/retrieval/` |
| E Workflow policy scenarios | **SIMULATED** | `research/results/workflow/` |

## What remains incomplete / Not evaluated

| Item | Why |
|------|-----|
| Human RAG answer quality (correctness, groundedness, citations) | No rated sample / judge protocol executed |
| Sentence-transformer / pretrained dense retrieval | Not installed/run in this pass (TF–IDF cosine used as lexical-vector comparator) |
| Optional reranking | Not run |
| Public IT ticket corpus ticket-category experiment | Deferred; synthetic AssistIQ intents used instead to avoid invalid label mapping |
| Live FCR / productivity user study | Only checklist-based SIMULATED times; explicitly not live productivity |
| Integration of research winners into production AssistIQ | Requires separate approval (Baseline A frozen) |

## Result-type discipline

- **MEASURED:** classification, routing, retrieval metrics on documented synthetic sets.  
- **SIMULATED:** workflow decisions + checklist timings.  
- **PROJECTED / Not evaluated:** live productivity gains; literature % as AssistIQ scores; human answer ratings.

## Production application

**Not modified.** Baseline A algorithms unchanged. Original methodology docs not overwritten (`AssistIQ_Methodology_Research_Report.docx` / prior plans retained). New paper section: `docs/research/AssistIQ_Solution_Methodology_3page.{md,docx}`.

## Reproduce

```powershell
cd research
pip install -r requirements-research.txt
python eval\build_datasets.py
python eval\run_classification.py
python eval\run_routing.py
python eval\run_retrieval.py
python eval\run_workflow_simulation.py
python eval\build_paper_section_docx.py
```
