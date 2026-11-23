from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "AssistIQ_Algorithmic_Flowcharts.docx"
FLOW = ROOT / "flowcharts"


def font(run, size=11, bold=False, italic=False):
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)


def main():
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2)
    sec.bottom_margin = Cm(2)
    sec.left_margin = Cm(2.2)
    sec.right_margin = Cm(2.2)

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("AssistIQ Algorithmic Flowcharts")
    font(r, 16, True)

    s = doc.add_paragraph()
    s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = s.add_run(
        "Methodology figures for Baseline A backend algorithms (not system architecture)"
    )
    font(r, 11, False, True)

    intro = doc.add_paragraph()
    intro.paragraph_format.first_line_indent = Cm(0.75)
    intro.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    r = intro.add_run(
        "These figures summarise the procedural logic implemented in AssistIQ Baseline A. "
        "Each diagram is an algorithmic flowchart: input, processing, decisions, and output. "
        "They are not UI maps and do not introduce methods absent from the codebase "
        "(no SVM, BERT, BM25, hybrid retrieval, real installs, or live password changes). "
        "Editable Mermaid sources are in AssistIQ_Algorithmic_Flowcharts.md."
    )
    font(r, 11)

    figures = [
        (
            "Figure A. Keyword-based intent detection in AssistIQ Baseline A "
            "(ordered substring match, question-mark fallback, optional lightweight "
            "hit-rate override only for knowledge_query).",
            "Figure_A_Intent_Detection.png",
            "Intent uses a fixed keyword order. The first substring hit wins; otherwise "
            "a question mark yields general_query and the default is knowledge_query. "
            "Any optional lightweight remapping is a hit-rate heuristic, not a trained classifier.",
        ),
        (
            "Figure B. Deterministic dictionary-based request routing in AssistIQ "
            "(INTENT_ROUTE_MAP).",
            "Figure_B_Request_Routing.png",
            "Routing is r(c)=INTENT_ROUTE_MAP[c]. Ticket chat intents retrieve ticket "
            "context; they do not insert ticket rows.",
        ),
        (
            "Figure C. Hash-v1 query/document embedding used by AssistIQ Baseline A "
            "(d=384, SHA-256 accumulation, L2 normalisation).",
            "Figure_C_Hash_Embedding.png",
            "hash-v1 is deterministic and untrained. Similarity mainly reflects shared "
            "hashed token mass.",
        ),
        (
            "Figure D. AssistIQ knowledge retrieval (k=3, cosine HNSW, published filter) "
            "and top-citation confidence thresholds (0.65 / 0.35).",
            "Figure_D_Retrieval_Confidence.png",
            "Confidence uses the top citation score only. NO_EVIDENCE may append a "
            "grounding warning; it does not auto-escalate.",
        ),
        (
            "Figure E. AssistIQ RAG generation path: constrained prompt, registry LLM, "
            "citation scrubbing, and confidence labelling.",
            "Figure_E_RAG_Generation.png",
            "Retrieved passages are treated as DATA. Generation does not guarantee "
            "factual correctness.",
        ),
        (
            "Figure F. AssistIQ IT/software-access decision algorithm "
            "(rule hierarchy and mock execution).",
            "Figure_F_IT_Decision.png",
            "Policy is rule-based. Terminal success uses MockExecutionAdapter only.",
        ),
        (
            "Figure G. AssistIQ password-reset decision algorithm "
            "(verify, risk, policy, confirm, mock IAM; TTL = 30 min).",
            "Figure_G_Password_Reset.png",
            "Identity and risk decisions are outside the LLM. Mock IAM does not change "
            "live passwords.",
        ),
    ]

    for cap, png, note in figures:
        doc.add_page_break()
        h = doc.add_heading(cap.split(".")[0], level=2)
        for run in h.runs:
            font(run, 13, True)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(FLOW / png), width=Inches(5.4))
        c = doc.add_paragraph()
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.paragraph_format.first_line_indent = Cm(0)
        r = c.add_run(cap)
        font(r, 10, False, True)
        n = doc.add_paragraph()
        n.paragraph_format.first_line_indent = Cm(0.75)
        n.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        r = n.add_run(note)
        font(r, 11)

    doc.save(OUT)
    print("Wrote", OUT)


if __name__ == "__main__":
    main()
