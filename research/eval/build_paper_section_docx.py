"""Build DOCX for the 3-page Solution/Methodology section from measured results."""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT.parent / "docs" / "research"
OUT = DOCS / "AssistIQ_Solution_Methodology_3page.docx"
MD = DOCS / "AssistIQ_Solution_Methodology_3page.md"


def font(run, size=11, bold=False, italic=False):
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)


def para(doc, text, *, size=11, bold=False, italic=False, indent=True, after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    if indent:
        p.paragraph_format.first_line_indent = Cm(0.5)
    else:
        p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run(text)
    font(r, size=size, bold=bold, italic=italic)
    return p


def heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        font(run, size=12 if level == 1 else 11, bold=True)
    h.paragraph_format.space_before = Pt(8)
    h.paragraph_format.space_after = Pt(4)


def add_table(doc, headers, rows):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Table Grid"
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        r = cell.paragraphs[0].add_run(h)
        font(r, 9, True)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = t.rows[ri + 1].cells[ci]
            cell.text = ""
            r = cell.paragraphs[0].add_run(str(val))
            font(r, 9)
    doc.add_paragraph()


def main():
    clf = json.loads((ROOT / "results" / "classification" / "metrics.json").read_text(encoding="utf-8"))
    rte = json.loads((ROOT / "results" / "routing" / "metrics.json").read_text(encoding="utf-8"))
    ret = json.loads((ROOT / "results" / "retrieval" / "metrics.json").read_text(encoding="utf-8"))
    wf = json.loads((ROOT / "results" / "workflow" / "metrics.json").read_text(encoding="utf-8"))

    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2)
    sec.bottom_margin = Cm(2)
    sec.left_margin = Cm(2.2)
    sec.right_margin = Cm(2.2)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run("Solution / Methodology / Mathematical Implementation")
    font(r, 14, True)

    para(
        doc,
        "Baseline A denotes algorithms in the AssistIQ application. Research Solution B "
        "denotes evaluation implementations under research/ that test intended completed-system "
        "methods. Results labelled MEASURED used locked synthetic AssistIQ-shaped datasets. "
        "Workflow timings are SIMULATED. Literature figures are not AssistIQ results. "
        "Generated-answer human ratings and live productivity studies are Not evaluated.",
        italic=True,
        indent=False,
        size=9,
    )

    heading(doc, "1. Proposed hybrid solution and technical implementation", 1)
    para(
        doc,
        "AssistIQ is designed as a hybrid IT helpdesk framework: deterministic intent "
        "identification and routing select a workflow; hash-based vector retrieval and an "
        "external LLM support knowledge answers; rule-based policy engines govern software/access "
        "and password-reset actions (mock adapters in the current build). The frozen application "
        "baseline (Baseline A) provides the production reference. Comparative classifiers, "
        "BM25/TF–IDF retrieval, and a workflow simulator were implemented only under research/ "
        "so experiments do not alter Baseline A code.",
    )

    heading(doc, "2. Four research features and algorithms", 1)
    para(
        doc,
        "Feature 1 — Intent classification. Baseline A assigns intent by ordered keyword "
        "substring matching. Research Solution B compares that detector with TF–IDF + Linear SVM, "
        "TF–IDF + logistic regression, and TF–IDF + random forest on the same held-out utterances.",
    )
    para(
        doc,
        "Feature 2 — Workflow routing. Baseline A maps intent c by r(c)=INTENT_ROUTE_MAP[c]. "
        "Research Solution B evaluates (i) keyword intent + map, (ii) a direct TF–IDF SVM route "
        "classifier, and (iii) oracle-intent + map. Chat ticket-creation intent routes to "
        "ticket-context retrieval and does not insert tickets.",
    )
    para(
        doc,
        "Feature 3 — RAG retrieval. Baseline A embeds text with hash-v1 (d=384), retrieves "
        "top-k=3 under cosine distance d_i, and scores s_i=max(0,1−d_i). Research Solution B "
        "compares hash-v1, BM25, and TF–IDF cosine on a fixed synthetic knowledge corpus with "
        "labelled qrels. Confidence uses s_top with thresholds 0.65/0.35 (heuristic). Dense "
        "sentence-transformer retrieval and human answer-quality rating are Not evaluated here.",
    )
    para(
        doc,
        "Feature 4 — End-to-end ITSM effectiveness. Baseline A encodes IT and password policies "
        "with mock execution/IAM. Research Solution B runs six scripted scenarios through the "
        "same policy rules and compares simulated step/time costs with a documented manual "
        "checklist. Outcomes are SIMULATED, not live wall-clock productivity.",
    )

    heading(doc, "3. Mathematical formulations and evaluation metrics", 1)
    para(
        doc,
        "Intent (Baseline A): I*(x) is the first intent I in fixed order O such that some "
        "keyword w in K_I is a substring of lowercased x; otherwise GENERAL_QUERY if “?” appears, "
        "else KNOWLEDGE_QUERY. Hash embedding: for SHA-256 byte b at index i and d=384, "
        "j=(b+i) mod d, v_j ← v_j + 1 + b/255, e = v/||v||_2. Retrieval: Recall@k = |L_1:k ∩ R|/|R|, "
        "MRR = average of 1/rank of first relevant hit, Hit@k = 1 if any relevant in top-k. "
        "Classification uses accuracy and macro-F1. Routing uses route accuracy, macro-F1, and "
        "false-automation rate (predicted IT/password route when gold is not). Workflow "
        "simulation uses completion = correct decisions/N and simulated FCR = correct and not ESCALATE / N.",
    )

    heading(doc, "4. Experimental setup", 1)
    para(
        doc,
        "Synthetic AssistIQ-shaped intent/routing data (n=339; train/val/test 237/51/51; seed 42) "
        "and a 10-chunk KB with 30 labelled queries (lexical vs paraphrase strata) were generated "
        "under research/datasets/ and marked synthetic. Classification and routing used "
        "scikit-learn; BM25 used rank_bm25. Workflow evaluation used six deterministic scenarios. "
        "No production application files were modified. Hypotheses (pre-result): H1 keyword ≠ "
        "TF–IDF classifiers; H2 map pipeline ≠ direct route classifier; H3 BM25/TF–IDF ≠ hash-v1 "
        "on Recall@3/MRR; H4 simulation yields completion/timing vs manual checklist (simulated only).",
    )

    heading(doc, "5. Compact results and interpretation", 1)
    para(doc, "Table 1. Intent classification (MEASURED, synthetic test n=51).", italic=True, indent=False, size=9)
    add_table(
        doc,
        ["Method", "Accuracy", "Macro-F1", "Type"],
        [
            ["Keyword Baseline A", f"{clf['keyword_baseline_a']['accuracy']:.3f}", f"{clf['keyword_baseline_a']['macro_f1']:.3f}", "MEASURED"],
            ["TF–IDF Linear SVM", f"{clf['tfidf_linear_svm']['accuracy']:.3f}", f"{clf['tfidf_linear_svm']['macro_f1']:.3f}", "MEASURED"],
            ["TF–IDF LogReg", f"{clf['tfidf_logreg']['accuracy']:.3f}", f"{clf['tfidf_logreg']['macro_f1']:.3f}", "MEASURED"],
            ["TF–IDF Random Forest", f"{clf['tfidf_random_forest']['accuracy']:.3f}", f"{clf['tfidf_random_forest']['macro_f1']:.3f}", "MEASURED"],
        ],
    )
    para(doc, "Table 2. Routing (MEASURED, synthetic test n=51).", italic=True, indent=False, size=9)
    add_table(
        doc,
        ["Method", "Route Acc.", "Macro-F1", "False-auto", "Type"],
        [
            [
                "Intent + map (A)",
                f"{rte['intent_plus_route_map']['route_accuracy']:.3f}",
                f"{rte['intent_plus_route_map']['macro_f1']:.3f}",
                f"{rte['intent_plus_route_map']['false_automation_rate']:.3f}",
                "MEASURED",
            ],
            [
                "Direct TF–IDF SVM",
                f"{rte['direct_tfidf_svm_route']['route_accuracy']:.3f}",
                f"{rte['direct_tfidf_svm_route']['macro_f1']:.3f}",
                f"{rte['direct_tfidf_svm_route']['false_automation_rate']:.3f}",
                "MEASURED",
            ],
            [
                "Oracle intent + map",
                f"{rte['oracle_intent_plus_map']['route_accuracy']:.3f}",
                f"{rte['oracle_intent_plus_map']['macro_f1']:.3f}",
                f"{rte['oracle_intent_plus_map']['false_automation_rate']:.3f}",
                "MEASURED",
            ],
        ],
    )
    para(doc, "Table 3. Retrieval @ k=3 (MEASURED, n=30 queries).", italic=True, indent=False, size=9)
    add_table(
        doc,
        ["Method", "Recall@3", "MRR", "Hit@3", "Type"],
        [
            [
                "hash-v1 (A-style)",
                f"{ret['hash_v1_chroma_style']['recall_at_3']:.3f}",
                f"{ret['hash_v1_chroma_style']['mrr']:.3f}",
                f"{ret['hash_v1_chroma_style']['hit_at_3']:.3f}",
                "MEASURED",
            ],
            [
                "BM25",
                f"{ret['bm25']['recall_at_3']:.3f}",
                f"{ret['bm25']['mrr']:.3f}",
                f"{ret['bm25']['hit_at_3']:.3f}",
                "MEASURED",
            ],
            [
                "TF–IDF cosine",
                f"{ret['tfidf_cosine']['recall_at_3']:.3f}",
                f"{ret['tfidf_cosine']['mrr']:.3f}",
                f"{ret['tfidf_cosine']['hit_at_3']:.3f}",
                "MEASURED",
            ],
        ],
    )
    para(doc, "Table 4. Workflow scenarios (SIMULATED, N=6).", italic=True, indent=False, size=9)
    add_table(
        doc,
        ["Metric", "Value", "Type"],
        [
            ["Task completion rate", f"{wf['task_completion_rate']:.3f}", "SIMULATED"],
            ["Escalation appropriateness", f"{wf['escalation_appropriateness']:.3f}", "SIMULATED"],
            ["FCR (sim. definition)", f"{wf['fcr_simulated']:.3f}", "SIMULATED"],
            [
                "Avg auto / manual minutes",
                f"{wf['avg_automated_minutes_sim']:.1f} / {wf['avg_manual_minutes_sim']:.1f}",
                "SIMULATED (not live productivity)",
            ],
            ["Answer-quality human ratings", "—", "Not evaluated"],
            ["Sentence-transformer dense IR", "—", "Not evaluated"],
        ],
    )
    para(
        doc,
        "Interpretation. On this synthetic AssistIQ-shaped test set, TF–IDF classifiers "
        "outperformed keyword intent (H1 supported here). Direct route classification "
        "outperformed intent+map while oracle+map reached perfect route accuracy, indicating "
        "residual map-pipeline error is largely intent error (H2 supported here). BM25 and "
        "TF–IDF cosine exceeded hash-v1 on Recall@3/MRR overall, with hash-v1 weaker on "
        "paraphrase queries (H3 supported here). Policy scenarios matched gold decisions under "
        "simulation; timing reductions are checklist-derived and must not be reported as "
        "measured productivity. Limitations: synthetic labels, small corpus/query counts, "
        "no human RAG answer study; literature SVM/BERT/FCR figures remain external context only.",
    )

    doc.save(OUT)
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
