# AssistIQ research-only evaluation

This directory is **not** the production AssistIQ application. It evaluates Research Solution B methods against Baseline A algorithms **without modifying** application source.

## Commands

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

## Outputs

- `datasets/` — synthetic AssistIQ-shaped data (see `DATASET_CARD.json`)
- `results/*/metrics.json` — raw metrics
- `results/*/predictions.json` — predictions
- `docs/research/AssistIQ_Solution_Methodology_3page.{md,docx}` — 3-page paper section
- `STATUS_REPORT.md` — measured vs simulated vs incomplete
