"""One-off builder for AssistIQ methodology report assets. Not part of the application runtime."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

OUT_DIR = Path(__file__).resolve().parent
PNG_PATH = OUT_DIR / "AssistIQ_Methodology_Architecture.png"
DOCX_PATH = OUT_DIR / "AssistIQ_Methodology_Research_Report.docx"
NOTE_PATH = OUT_DIR / "AssistIQ_Methodology_Verification_Note.txt"


def _font(size: int, bold: bool = False):
    candidates = [
        r"C:\Windows\Fonts\calibri.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
    ]
    bold_candidates = [
        r"C:\Windows\Fonts\calibrib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\segoeuib.ttf",
    ]
    paths = bold_candidates if bold else candidates
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_box(draw, xy, text, fill, outline, font, radius=10):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=2)
    # center multiline text
    lines = text.split("\n")
    heights = []
    widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    total_h = sum(heights) + (len(lines) - 1) * 4
    cy = y0 + (y1 - y0 - total_h) / 2
    for line, h, w in zip(lines, heights, widths):
        cx = x0 + (x1 - x0 - w) / 2
        draw.text((cx, cy), line, fill=(30, 30, 30), font=font)
        cy += h + 4


def draw_arrow(draw, x1, y1, x2, y2, color=(70, 70, 70)):
    draw.line((x1, y1, x2, y2), fill=color, width=2)
    # simple arrow head
    if abs(y2 - y1) >= abs(x2 - x1):
        # vertical
        draw.polygon([(x2, y2), (x2 - 5, y2 - 8), (x2 + 5, y2 - 8)], fill=color)
    else:
        if x2 > x1:
            draw.polygon([(x2, y2), (x2 - 8, y2 - 5), (x2 - 8, y2 + 5)], fill=color)
        else:
            draw.polygon([(x2, y2), (x2 + 8, y2 - 5), (x2 + 8, y2 + 5)], fill=color)


def build_figure():
    W, H = 1600, 2000
    img = Image.new("RGB", (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    title_f = _font(28, bold=True)
    box_f = _font(20, bold=True)
    small_f = _font(16)

    # palette: muted academic
    fill_n = (245, 247, 250)
    fill_a = (232, 240, 248)  # blue-gray for RAG
    fill_b = (243, 240, 235)  # warm gray for IT
    fill_c = (240, 243, 238)  # green-gray for password
    fill_e = (248, 240, 240)  # soft red for escalate
    outline = (90, 98, 110)

    cx = W // 2
    # USER
    draw_box(draw, (cx - 120, 40, cx + 120, 100), "USER", fill_n, outline, box_f)
    draw_arrow(draw, cx, 100, cx, 130)

    draw_box(draw, (cx - 200, 130, cx + 200, 200), "Chat / ITSM Interface", fill_n, outline, box_f)
    draw_arrow(draw, cx, 200, cx, 230)

    draw_box(draw, (cx - 180, 230, cx + 180, 300), "Intent Detection", fill_n, outline, box_f)
    draw_arrow(draw, cx, 300, cx, 330)

    draw_box(draw, (cx - 180, 330, cx + 180, 400), "Request Routing", fill_n, outline, box_f)

    # branch stem
    draw_arrow(draw, cx, 400, cx, 450)
    # horizontal split
    y_split = 450
    x_rag, x_it, x_pw = 280, 800, 1320
    draw.line((x_rag, y_split, x_pw, y_split), fill=(70, 70, 70), width=2)
    # escalate side
    x_esc = 1480
    draw.line((cx, y_split, x_esc, y_split), fill=(70, 70, 70), width=2)

    for x in (x_rag, x_it, x_pw):
        draw_arrow(draw, x, y_split, x, 490)

    # Escalation branch up-right label
    draw_arrow(draw, x_esc, y_split, x_esc, 490)
    draw_box(
        draw,
        (x_esc - 130, 490, x_esc + 130, 580),
        "Human\nEscalation",
        fill_e,
        outline,
        small_f,
    )

    # Three main branches
    draw_box(draw, (x_rag - 150, 490, x_rag + 150, 580), "Knowledge / RAG", fill_a, outline, box_f)
    draw_box(draw, (x_it - 150, 490, x_it + 150, 580), "IT Requests", fill_b, outline, box_f)
    draw_box(draw, (x_pw - 150, 490, x_pw + 150, 580), "Password Reset", fill_c, outline, box_f)

    for x in (x_rag, x_it, x_pw):
        draw_arrow(draw, x, 580, x, 620)

    draw_box(draw, (x_rag - 150, 620, x_rag + 150, 710), "Retrieval\n(top-k = 3)", fill_a, outline, small_f)
    draw_box(draw, (x_it - 150, 620, x_it + 150, 710), "Policy\nEvaluation", fill_b, outline, small_f)
    draw_box(draw, (x_pw - 150, 620, x_pw + 150, 710), "Verification", fill_c, outline, small_f)

    for x in (x_rag, x_it, x_pw):
        draw_arrow(draw, x, 710, x, 750)

    draw_box(draw, (x_rag - 150, 750, x_rag + 150, 840), "Context + LLM", fill_a, outline, small_f)
    draw_box(draw, (x_it - 150, 750, x_it + 150, 840), "Approval /\nMock Execution", fill_b, outline, small_f)
    draw_box(draw, (x_pw - 150, 750, x_pw + 150, 840), "Risk + Policy /\nMock IAM", fill_c, outline, small_f)

    # merge
    y_merge_top = 880
    for x in (x_rag, x_it, x_pw):
        draw.line((x, 840, x, y_merge_top), fill=(70, 70, 70), width=2)
    draw.line((x_rag, y_merge_top, x_pw, y_merge_top), fill=(70, 70, 70), width=2)
    draw_arrow(draw, cx, y_merge_top, cx, 920)

    # also connect escalation lightly into response? Keep separate - arrow down from esc to response area
    draw.line((x_esc, 580, x_esc, y_merge_top), fill=(70, 70, 70), width=2)
    draw.line((x_esc, y_merge_top, x_pw, y_merge_top), fill=(70, 70, 70), width=2)

    draw_box(draw, (cx - 200, 920, cx + 200, 990), "Response / Action", fill_n, outline, box_f)
    draw_arrow(draw, cx, 990, cx, 1020)

    draw_box(
        draw,
        (cx - 220, 1020, cx + 220, 1090),
        "Citation + Confidence Check",
        fill_n,
        outline,
        box_f,
    )
    draw_arrow(draw, cx, 1090, cx, 1120)

    draw_box(draw, (cx - 120, 1120, cx + 120, 1180), "USER", fill_n, outline, box_f)

    # footer note
    note = (
        "AssistIQ processing flow (implementation Baseline A). "
        "LLM generation is used on the knowledge/ticket response path; "
        "IT and password outcomes follow rule-based policy with mock adapters."
    )
    draw.text((60, 1240), note, fill=(80, 80, 80), font=small_f)

    # Crop whitespace
    bbox = img.getbbox()
    # keep white margin
    cropped = img.crop((0, 0, W, 1320))
    cropped.save(PNG_PATH, dpi=(300, 300))
    print("Wrote", PNG_PATH)


def set_run_font(run, size=11, bold=False, italic=False, name="Times New Roman"):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)


def add_para(doc, text, *, size=11, bold=False, italic=False, first_line=True, space_after=8):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(0)
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    if first_line:
        pf.first_line_indent = Cm(0.75)
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, italic=italic)
    return p


def add_heading_custom(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        set_run_font(run, size=14 if level == 1 else 12 if level == 2 else 11, bold=True)
    h.paragraph_format.space_before = Pt(14)
    h.paragraph_format.space_after = Pt(8)
    return h


def add_equation(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.first_line_indent = Cm(0)
    run = p.add_run(text)
    set_run_font(run, size=11, italic=True)
    return p


def add_table(doc, headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        set_run_font(run, size=10, bold=True)
    for r_i, row in enumerate(rows):
        for c_i, val in enumerate(row):
            cell = table.rows[r_i + 1].cells[c_i]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(val))
            set_run_font(run, size=10)
    doc.add_paragraph()


def build_docx():
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

    # Title block
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("AssistIQ: Methodology and System Design")
    set_run_font(r, size=16, bold=True)

    st = doc.add_paragraph()
    st.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = st.add_run(
        "Research methodology report for an intelligent IT service management assistant "
        "(implementation Baseline A)"
    )
    set_run_font(r, size=11, italic=True)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = meta.add_run(
        "Document type: academic methodology section · Source of truth: AssistIQ repository implementation"
    )
    set_run_font(r, size=9, italic=True)

    add_heading_custom(doc, "3. Methodology", level=1)

    add_para(
        doc,
        "This section describes how AssistIQ processes IT support requests in the form "
        "currently implemented in the project codebase. The account is limited to verified "
        "behaviour: deterministic intent labelling, dictionary-based routing, hash-based "
        "retrieval features, retrieval-augmented answer generation, and rule-governed "
        "software-access and password-reset workflows that terminate in mock adapters. "
        "Where later evaluation datasets or quantitative scores are still missing, that "
        "absence is stated directly rather than filled with assumed performance.",
        first_line=True,
    )

    add_heading_custom(doc, "3.1 Graphical Overview of the Proposed AssistIQ Framework", level=2)

    add_para(
        doc,
        "Figure 1 summarises the main control flow. A user reaches AssistIQ through the "
        "chat interface or through the conventional ITSM screens for tickets, knowledge, "
        "IT requests, and password resets. Chat messages first pass through intent "
        "detection and then through a fixed routing map. From that point the system "
        "branches: knowledge-oriented turns enter retrieval and grounded generation; "
        "software and access requests enter catalog matching and policy evaluation; "
        "password-reset turns enter identity verification, risk assessment, and policy "
        "checks; and explicit requests for a human agent enter an escalation response. "
        "Citation checks and a similarity-based confidence label close the generative path.",
        first_line=True,
    )

    # Insert figure
    p_fig = doc.add_paragraph()
    p_fig.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_fig.paragraph_format.first_line_indent = Cm(0)
    p_fig.add_run().add_picture(str(PNG_PATH), width=Inches(5.8))

    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.first_line_indent = Cm(0)
    cap.paragraph_format.space_after = Pt(12)
    r = cap.add_run(
        "Figure 1. High-level architecture and processing flow of the AssistIQ "
        "intelligent IT service management framework."
    )
    set_run_font(r, size=10, italic=True)

    add_para(
        doc,
        "The figure is intentionally coarse. It does not enumerate every keyword list, "
        "database table, or configuration constant. Those details appear in the algorithmic "
        "subsections that follow. What the diagram is meant to make obvious is the "
        "separation between generative answering and policy-controlled action: the language "
        "model is used to draft grounded responses, not to authorise software changes or "
        "credential resets.",
        first_line=True,
    )

    add_heading_custom(doc, "3.2 System Architecture", level=2)

    add_para(
        doc,
        "AssistIQ is organised as a conversation and workflow graph rather than as a single "
        "monolithic predictor. After authentication, employees, agents, and administrators "
        "work inside role-scoped screens. Chat traffic is orchestrated by a LangGraph state "
        "machine that starts at intent detection, records a route, and then enters one of "
        "the specialised nodes. Relational state (users, tickets, knowledge documents, "
        "workflow records, telemetry) lives in PostgreSQL. Chunk vectors used for retrieval "
        "are stored in a persistent Chroma collection, while document text and publication "
        "status remain authoritative in PostgreSQL.",
        first_line=True,
    )

    add_para(
        doc,
        "The knowledge branch exists because many IT questions are answered from written "
        "procedures. Embedding the query, retrieving a short list of published chunks, and "
        "only then calling the language model is a deliberate ordering: unsupported text "
        "should not be invented when the corpus is empty or weakly related. Ticket-oriented "
        "chat intents load recent tickets belonging to the user and ask the model to reply "
        "in that context. Creating a ticket record, however, remains a separate form-based "
        "workflow in which category and priority are chosen explicitly. That distinction "
        "matters for the paper: a chat intent named ticket_creation_request currently "
        "means “talk about tickets,” not “insert a ticket row.”",
        first_line=True,
    )

    add_para(
        doc,
        "The IT-request and password-reset branches exist because unconstrained generation "
        "is a poor gatekeeper for privileged operations. In those paths AssistIQ extracts "
        "structured cues, consults allow-listed catalogs or identity checks, and applies "
        "hand-written policy. Allowed outcomes may proceed only through MockExecutionAdapter "
        "or MockIAMAdapter, which return simulated results and do not install packages or "
        "rewrite login credentials. Human escalation is available both as an explicit intent "
        "and as a policy outcome when extraction confidence is low or risk is high. After "
        "generative turns, citation scrubbing and a thresholded confidence label give the "
        "interface a compact signal of how strongly retrieval supported the answer.",
        first_line=True,
    )

    add_para(
        doc,
        "Taken together, the architecture trades end-to-end learned autonomy for inspectable "
        "control. Baseline A therefore freezes the keyword tables, route map, hash embedding, "
        "retrieval depth, confidence cut-offs, and policy rules so that later experiments "
        "can measure those components against labelled data instead of changing them "
        "opportunistically during demos.",
        first_line=True,
    )

    add_heading_custom(doc, "3.3 Algorithmic Methodology", level=2)

    add_heading_custom(doc, "3.3.1 Intent Detection", level=3)

    add_para(
        doc,
        "Intent detection assigns each chat utterance to one of a fixed set of labels that "
        "the router understands. Let x denote the user message and let ℓ(x) be its "
        "lowercased form. For each intent class c the implementation stores a keyword set "
        "K_c. Classes are examined in a fixed order: human escalation, password-reset "
        "request, software/access request, ticket-creation request, ticket query, and "
        "knowledge query. The first class for which any keyword appears as a substring of "
        "ℓ(x) wins. If no keyword matches, a question mark in x yields general_query; "
        "otherwise the label defaults to knowledge_query.",
        first_line=True,
    )

    add_equation(
        doc,
        "ĉ_kw(x) = c_j  if j = min{ i | ∃ w ∈ K_{c_i} with w ⊆ ℓ(x) }, "
        "else GENERAL_QUERY if “?” ∈ x, else KNOWLEDGE_QUERY.",
    )

    add_para(
        doc,
        "This rule is a deterministic lexical heuristic. It is not a trained classifier: "
        "there is no labelled optimisation of K_c inside AssistIQ, and no probabilistic "
        "score is returned by the keyword pass. When a lightweight registry model is "
        "configured and the keyword result is still knowledge_query, an optional adapter "
        "may propose a remapping based on per-label token hit rates. That adapter is a "
        "local scoring routine packaged under a “lightweight ML” provider name; it is not "
        "a fitted SVM or logistic regression model shipped with learned weights. Errors in "
        "the optional path are swallowed and the keyword label is kept.",
        first_line=True,
    )

    add_heading_custom(doc, "3.3.2 Request Routing", level=3)

    add_para(
        doc,
        "Routing converts the intent string into a LangGraph node name. The mapping is a "
        "constant dictionary rather than a learned dispatcher:",
        first_line=True,
    )

    add_equation(doc, "r(c) = INTENT_ROUTE_MAP[c]  (default: handle_unsupported).")

    add_para(
        doc,
        "In the current build, knowledge_query and general_query both enter retrieve_context; "
        "ticket_query and ticket_creation_request enter retrieve_ticket_context; "
        "password_reset_request enters start_password_reset; software_access_request enters "
        "start_it_request; human_escalation enters escalate; and unsupported labels enter "
        "handle_unsupported. Because the map is exhaustive and static, measured routing "
        "mistakes in later experiments will mostly reflect intent mistakes rather than a "
        "separate routing model.",
        first_line=True,
    )

    add_heading_custom(doc, "3.3.3 Query Embedding", level=3)

    add_para(
        doc,
        "Retrieval features are produced by HashEmbeddingService under the identifier "
        "hash-v1. Text is lowercased, trimmed, and whitespace-collapsed, then split on "
        "spaces. For dimension d = 384 the method accumulates a sparse bag over hashed "
        "token bytes. If b is byte i of the SHA-256 digest of a token,",
        first_line=True,
    )

    add_equation(doc, "j = (b + i) mod d,    v_j ← v_j + 1 + b/255.")

    add_para(
        doc,
        "After all tokens are processed, the vector is L2-normalised when its norm is "
        "non-zero:",
        first_line=True,
    )

    add_equation(doc, "e = v / ∥v∥₂.")

    add_para(
        doc,
        "The same transform is applied to chunks at ingest and to queries at search time. "
        "The representation is reproducible and free of an external embedding server, which "
        "is useful for a frozen baseline. It does not learn synonymy from data; similarity "
        "mainly reflects shared token-hash mass. That limitation is accepted for Baseline A "
        "and is one of the hypotheses later retrieval experiments are meant to test.",
        first_line=True,
    )

    add_heading_custom(doc, "3.3.4 Vector Retrieval", level=3)

    add_para(
        doc,
        "Published knowledge is retrieved in three steps. First the query embedding is "
        "computed. Second, ChromaDB performs an HNSW search in cosine space over the "
        "kb_chunks collection with a metadata filter requiring published status, returning "
        "k = 3 neighbours. Third, each hit is joined back to PostgreSQL document and chunk "
        "rows that are still published, so draft or deleted material cannot leak through a "
        "stale vector id. Chroma distances d_i are converted for application use as",
        first_line=True,
    )

    add_equation(doc, "s_i = max(0, 1 − d_i).")

    add_para(
        doc,
        "The ranked list supplies citation payloads and defines s_max as the score of the "
        "first surviving hit. Retrieval depth k = 3 is a configuration choice in Baseline A, "
        "not a measured optimum.",
        first_line=True,
    )

    add_heading_custom(doc, "3.3.5 Confidence Estimation", level=3)

    add_para(
        doc,
        "After retrieval (and, on the streaming path, after prompt preparation), AssistIQ "
        "attaches a coarse confidence label. The implementation inspects the top citation "
        "score s_max rather than averaging all returned scores. With thresholds 0.65 and "
        "0.35 the piecewise rule is",
        first_line=True,
    )

    add_equation(
        doc,
        "C = HIGH_CONFIDENCE if s_max ≥ 0.65 and citations exist; "
        "LOW_CONFIDENCE if 0.35 ≤ s_max < 0.65; "
        "NO_EVIDENCE otherwise (including empty retrieval).",
    )

    add_para(
        doc,
        "For knowledge and general intents labelled NO_EVIDENCE, a short warning is appended "
        "to the answer text. The label is an operational heuristic tied to retrieval "
        "similarity. It should not be read as a calibrated probability of answer "
        "correctness.",
        first_line=True,
    )

    add_heading_custom(doc, "3.3.6 Retrieval-Augmented Generation", level=3)

    add_para(
        doc,
        "On the knowledge path the pipeline is: query embedding, vector retrieval, prompt "
        "construction, language-model generation, structural citation checks, and confidence "
        "labelling. The prompt states system rules that treat retrieved passages as DATA "
        "rather than as instructions, includes at most the last six conversation turns "
        "truncated to 400 characters each, inserts up to five knowledge blocks truncated "
        "to 500 characters with [KB-n] markers, and restates the current question. Under "
        "Baseline A at most three chunks arrive from retrieval, so the five-block prompt "
        "cap is an upper bound rather than a guarantee of five evidence items. Generation "
        "is performed by an enabled registry LLM (commonly reached through an "
        "OpenAI-compatible local endpoint such as Ollama in the development configuration). "
        "AssistIQ does not train that model. Citation validation keeps structured references "
        "that carry document and chunk identifiers; it does not prove that every sentence "
        "in the answer is entailed by the corpus.",
        first_line=True,
    )

    add_heading_custom(doc, "3.3.7 IT Request Decision Process", level=3)

    add_para(
        doc,
        "Software and access requests are handled outside free-form generation. The message "
        "is typed as PERMISSION, ACCESS, or SOFTWARE using keyword cues. Catalog names and "
        "aliases are matched by longest substring containment. Extraction confidence is set "
        "to 0.9 on a catalog hit and 0.35 otherwise, and is capped at 0.6 for permission-type "
        "requests. Unmatched non-permission requests may escalate for clarification. Policy "
        "evaluation then returns DENY, ESCALATE, APPROVAL_REQUIRED, or ALLOW according to "
        "catalog membership, enablement, catalog risk, approval flags, and privileged "
        "language. Only allow or previously approved paths call MockExecutionAdapter, which "
        "returns a simulated execution record. No host software is installed and no real "
        "access grant is performed in the present implementation.",
        first_line=True,
    )

    add_heading_custom(doc, "3.3.8 Password Reset Decision Process", level=3)

    add_para(
        doc,
        "Password-reset chat turns open a request in a verification-required state with a "
        "thirty-minute expiry. Identity verification compares the submitted email with the "
        "authenticated actor and rejects or escalates suspicious self-assertions and "
        "cross-user employee attempts. Risk assessment raises the level for third-party "
        "language, repeated verification failure, privileged target accounts, and related "
        "cases. Policy then denies, requires confirmation, or escalates; high and critical "
        "risk are not auto-executed. Explicit confirmation precedes MockIAMAdapter, which "
        "simulates a reset and leaves the stored password hash and any external directory "
        "unchanged. The language model is not the authority for allow or deny decisions on "
        "this path.",
        first_line=True,
    )

    add_heading_custom(doc, "3.4 Data Collection", level=2)

    add_para(
        doc,
        "Two kinds of data must be distinguished. The first is operational data that the "
        "running application can already store. The second is labelled research data needed "
        "to score Baseline A quantitatively. Mixing the two leads to false claims of "
        "evaluation readiness.",
        first_line=True,
    )

    add_para(
        doc,
        "Operational stores present in the implementation include knowledge documents and "
        "chunks with publication status; Chroma vectors for those chunks; tickets with "
        "comments and events; IT requests with entities, approvals, executions, and workflow "
        "events; password-reset requests with verification and policy telemetry; chat "
        "conversations, messages, and citations; AI model registry and inference telemetry; "
        "and audit events consumed by observability views. These tables support demos and "
        "debugging. They are not, by themselves, a frozen annotated benchmark.",
        first_line=True,
    )

    add_para(
        doc,
        "For research scoring, four planned evaluation datasets are required and are not "
        "treated here as already collected. An intent dataset should target on the order of "
        "five hundred utterances where feasible, with roughly fifty examples per class when "
        "possible, and a stratified seventy/fifteen/fifteen split into train, validation, "
        "and locked test partitions. A routing dataset should target at least four hundred "
        "utterances with gold workflow-node labels and explicit false-automation cases. A "
        "RAG relevance set should target at least one hundred queries over the AssistIQ "
        "knowledge base with multiple judgments per query and strata for high lexical "
        "overlap versus paraphrase or low overlap. An end-to-end scenario pack should target "
        "at least forty scripted tasks covering knowledge Q&A, tickets, IT mock requests, "
        "password reset, escalation, and multi-step cases. Until those artefacts exist in "
        "the project, they remain planned evaluation datasets.",
        first_line=True,
    )

    add_heading_custom(doc, "3.5 Experimental Setup and Evaluation Metrics", level=2)

    add_para(
        doc,
        "The experimental programme attached to Baseline A is comparative and offline first. "
        "Intent labelling is scored with accuracy, per-class precision, recall, and F1, "
        "together with a confusion matrix that exposes paraphrase and multi-intent failures. "
        "Routing is scored with route accuracy, joint intent-to-route accuracy, and "
        "false-automation rate on IT and password paths. Retrieval at k = 3 is scored with "
        "Precision@3, Recall@3, Hit@3, and mean reciprocal rank, preferably broken out by "
        "lexical-overlap strata. Scenario runs report task completion rate, escalation rate, "
        "interaction steps, and completion time under a written rubric.",
        first_line=True,
    )

    add_para(
        doc,
        "Metrics such as first-contact resolution, agent productivity, and solution "
        "retention appear in related literature and motivate the project, but they are not "
        "automatic by-products of the current code. Each requires an AssistIQ-specific "
        "definition and a protocol on the scenario pack before any numeric claim is "
        "defensible. Observability endpoints in the application currently return the "
        "placeholder status “Not evaluated” for retrieval quality fields, which matches the "
        "absence of locked qrels in the repository.",
        first_line=True,
    )

    add_heading_custom(doc, "3.6 Results", level=2)

    add_para(
        doc,
        "Results are reported in two layers so that configuration values are not mistaken "
        "for measured performance.",
        first_line=True,
    )

    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run("Table 1. Verified Baseline A system parameters (not performance scores).")
    set_run_font(r, size=10, italic=True)

    add_table(
        doc,
        ["Parameter", "Verified value", "Role"],
        [
            ["Embedding identifier", "hash-v1", "Feature representation"],
            ["Embedding dimension", "384", "Vector length"],
            ["Chunk size / overlap", "800 / 120", "Ingestion"],
            ["Retrieval depth k", "3", "Chroma top-k"],
            ["Confidence thresholds", "0.65 / 0.35", "Heuristic cut-offs on s_max"],
            ["History in prompt", "6 turns × 400 characters", "Prompt construction"],
            ["KB block limits", "≤5 blocks × 500 characters", "Prompt construction"],
            ["Password request TTL", "30 minutes", "Workflow expiry"],
        ],
    )

    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run("Table 2. AssistIQ experimental measurements available in the repository.")
    set_run_font(r, size=10, italic=True)

    add_table(
        doc,
        ["Metric family", "Status", "Notes"],
        [
            ["Intent accuracy / F1", "Not yet measured", "No locked labelled intent set in-repo"],
            ["Route accuracy / false automation", "Not yet measured", "No gold routing set in-repo"],
            ["Precision@3, Recall@3, Hit@3, MRR", "Not yet measured", "Observability returns “Not evaluated”"],
            ["Scenario completion / escalation", "Not yet measured", "Scenario pack not collected"],
            ["AssistIQ FCR / productivity / retention", "Not yet measured", "Protocol not executed"],
        ],
    )

    add_para(
        doc,
        "External figures that appear in project literature notes (for example, reported "
        "SVM ticket-classification accuracy, BERT routing accuracy, field solution "
        "retention, or agentic ITSM gains in prior publications) belong to those earlier "
        "studies. They are motivation for AssistIQ’s research questions and are not "
        "results of this system.",
        first_line=True,
    )

    add_heading_custom(doc, "3.7 Limitations", level=2)

    add_para(
        doc,
        "Several limitations follow directly from Baseline A design choices. Keyword intent "
        "detection is transparent and cheap, yet utterances that avoid listed substrings, "
        "or that combine several goals in one sentence, can be mislabelled. Because routing "
        "is a dictionary over those labels, such mistakes propagate into the wrong workflow. "
        "Hash embeddings likewise favour token overlap; they are a weak stand-in for "
        "semantic paraphrase retrieval until qrels show otherwise.",
        first_line=True,
    )

    add_para(
        doc,
        "Confidence labels inherit the same retrieval scores and use fixed cut-offs. They "
        "help the interface signal thin evidence, but they are not a substitute for human "
        "review when answers affect access or security. The generative stack can still "
        "produce fluent unsupported statements when retrieval is weak; treating documents "
        "as DATA reduces one failure mode (instruction injection) without removing "
        "hallucination in general.",
        first_line=True,
    )

    add_para(
        doc,
        "On the automation side, mock execution and mock IAM are appropriate for a safe "
        "academic prototype, yet they also block claims about real install success or "
        "directory password changes. Finally, the project still lacks locked labelled "
        "sets and therefore lacks AssistIQ-owned accuracy, ranking, and end-to-end "
        "effectiveness numbers. Local LLM latency and cold-start behaviour also affect "
        "perceived responsiveness in demos, which is an engineering constraint rather than "
        "an information-retrieval metric.",
        first_line=True,
    )

    add_heading_custom(doc, "3.8 Research Claim Status", level=2)

    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    r = p.add_run("Table 3. Status of research claims relative to the current AssistIQ evidence.")
    set_run_font(r, size=10, italic=True)

    add_table(
        doc,
        ["Category", "Claims"],
        [
            [
                "Verified by implementation",
                "LangGraph chat topology; ordered keyword intent; INTENT_ROUTE_MAP; "
                "hash-v1 (d=384); chunking 800/120; Chroma cosine HNSW with k=3 and "
                "published-only join; confidence heuristic on s_max with 0.65/0.35; "
                "RAG prompt DATA framing and [KB-n] limits; rule-based IT and password "
                "policies ending in mock adapters; manual ticket categories on create; "
                "chat ticket intents retrieve context rather than insert tickets.",
            ],
            [
                "Measured experimentally",
                "None for AssistIQ intent, routing, retrieval, or end-to-end quality "
                "metrics in the repository at the time of this report.",
            ],
            [
                "Not yet measured / future work",
                "Construction of planned labelled datasets; Baseline A offline scores; "
                "AssistIQ-defined FCR, productivity, and retention protocols; ablations "
                "that alter frozen Baseline A components after gap validation.",
            ],
        ],
    )

    add_para(
        doc,
        "The practical implication for writing and review is narrow: architecture and "
        "algorithm descriptions may be asserted from the codebase, while performance "
        "comparisons must wait for the planned evaluation materials. Keeping those "
        "categories separate is part of the methodology rather than an afterthought.",
        first_line=True,
    )

    # Footer note
    end = doc.add_paragraph()
    end.paragraph_format.first_line_indent = Cm(0)
    end.paragraph_format.space_before = Pt(18)
    r = end.add_run(
        "End of methodology report. Application source code was not modified during preparation of this document."
    )
    set_run_font(r, size=9, italic=True)

    # Simple page field via sectPr is complex; add footer with page hint text
    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run("AssistIQ Methodology Research Report")
    set_run_font(run, size=9, italic=True)

    doc.save(DOCX_PATH)
    print("Wrote", DOCX_PATH)


def write_note():
    text = """AssistIQ Methodology Report — Verification Note
================================================

Files created
-------------
1) docs/research/AssistIQ_Methodology_Research_Report.docx
2) docs/research/AssistIQ_Methodology_Architecture.png
3) docs/research/AssistIQ_Methodology_Verification_Note.txt
4) docs/research/_build_methodology_report.py  (builder script only; not application runtime)

Application / source-code files modified
----------------------------------------
None.

Implementation sources inspected
--------------------------------
- backend/app/agents/graphs/chat_graph.py
- backend/app/agents/intents.py
- backend/app/agents/nodes/detect_intent.py
- backend/app/agents/nodes/route_request.py
- backend/app/agents/nodes/retrieve_context.py
- backend/app/agents/nodes/confidence_check.py
- backend/app/agents/nodes/generate_answer.py
- backend/app/agents/prompts.py
- backend/app/agents/nodes/start_it_request.py
- backend/app/agents/nodes/start_password_reset.py
- backend/app/services/embedding_service.py
- backend/app/adapters/chroma.py
- backend/app/services/knowledge_base_service.py
- backend/app/services/entity_extraction.py
- backend/app/services/policy_service.py
- backend/app/services/password_reset_service.py
- backend/app/services/password_verification.py
- backend/app/services/password_risk.py
- backend/app/services/password_reset_policy.py
- backend/app/execution/adapter.py
- backend/app/iam/adapter.py
- backend/app/core/config.py
- backend/app/services/observability_service.py
- backend/tests/test_observability.py

Claims verified against implementation
--------------------------------------
- Keyword intent (ordered groups) and optional lightweight override only for knowledge_query
- Deterministic INTENT_ROUTE_MAP values listed in the report
- hash-v1, d=384, SHA-256 bag + L2
- Chroma cosine HNSW, published filter, k=3, s=max(0,1-d)
- Confidence on top score with 0.65 / 0.35
- RAG prompt limits (6×400 history; ≤5×500 KB blocks; DATA framing)
- IT mock execution; password mock IAM; TTL 30 minutes
- Ticket chat path does not auto-create tickets
- Observability IR metrics status "Not evaluated"

Measurements still missing
--------------------------
- AssistIQ intent / routing / retrieval / scenario numeric results
- Locked labelled datasets (intent, routing, qrels, scenarios)
- AssistIQ-defined FCR, productivity, retention measurements

Literature percentages cited in other project docs were NOT used as AssistIQ results.
"""
    NOTE_PATH.write_text(text, encoding="utf-8")
    print("Wrote", NOTE_PATH)


if __name__ == "__main__":
    build_figure()
    build_docx()
    write_note()
