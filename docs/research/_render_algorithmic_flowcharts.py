"""Render compact academic algorithmic flowchart PNGs for AssistIQ paper figures A–G."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "flowcharts"
OUT.mkdir(exist_ok=True)

FILL = (245, 247, 250)
FILL_D = (232, 241, 248)
FILL_M = (222, 235, 247)
FILL_W = (252, 228, 214)
OUTLINE = (68, 84, 106)
OUTLINE_D = (31, 78, 121)
TEXT = (30, 30, 30)


def font(size: int, bold: bool = False):
    paths = (
        [r"C:\Windows\Fonts\calibrib.ttf", r"C:\Windows\Fonts\arialbd.ttf"]
        if bold
        else [r"C:\Windows\Fonts\calibri.ttf", r"C:\Windows\Fonts\arial.ttf"]
    )
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


def text_size(draw, text, fnt):
    lines = text.split("\n")
    widths, heights = [], []
    for line in lines:
        b = draw.textbbox((0, 0), line, font=fnt)
        widths.append(b[2] - b[0])
        heights.append(b[3] - b[1])
    return max(widths) if widths else 0, sum(heights) + 3 * (len(lines) - 1), lines, heights


def box(draw, cx, y, w, h, text, fnt, fill=FILL, outline=OUTLINE, diamond=False):
    x0, y0, x1, y1 = cx - w // 2, y, cx + w // 2, y + h
    if diamond:
        mid_y = (y0 + y1) // 2
        pts = [(cx, y0), (x1, mid_y), (cx, y1), (x0, mid_y)]
        draw.polygon(pts, fill=FILL_D, outline=OUTLINE_D)
    else:
        draw.rounded_rectangle((x0, y0, x1, y1), radius=8, fill=fill, outline=outline, width=2)
    tw, th, lines, heights = text_size(draw, text, fnt)
    cy = y0 + (h - th) / 2
    for line, hh in zip(lines, heights):
        b = draw.textbbox((0, 0), line, font=fnt)
        lw = b[2] - b[0]
        draw.text((cx - lw / 2, cy), line, fill=TEXT, font=fnt)
        cy += hh + 3
    return y1


def arrow(draw, x, y0, y1):
    draw.line((x, y0, x, y1), fill=(70, 70, 70), width=2)
    draw.polygon([(x, y1), (x - 5, y1 - 8), (x + 5, y1 - 8)], fill=(70, 70, 70))


def caption(draw, w, y, text, fnt):
    draw.text((24, y), text, fill=(80, 80, 80), font=fnt)
    return y + 36


def stack(name, title, steps, width=720, step_h=48, gap=22):
    f_title = font(18, True)
    f_box = font(14, True)
    f_cap = font(12)
    # estimate height
    h = 70
    for kind, _ in steps:
        h += (step_h + 10 if kind == "d" else step_h) + gap
    h += 80
    img = Image.new("RGB", (width, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((24, 16), title, fill=TEXT, font=f_title)
    cx = width // 2
    y = 56
    for i, (kind, text) in enumerate(steps):
        bw = min(width - 80, 520 if kind != "d" else 460)
        bh = step_h + (8 if kind == "d" else 0)
        if kind == "m":
            fill, outline = FILL_M, OUTLINE_D
        elif kind == "w":
            fill, outline = FILL_W, (198, 89, 17)
        else:
            fill, outline = FILL, OUTLINE
        y1 = box(draw, cx, y, bw, bh, text, f_box, fill=fill, outline=outline, diamond=(kind == "d"))
        if i < len(steps) - 1:
            arrow(draw, cx, y1, y1 + gap - 2)
            y = y1 + gap
        else:
            y = y1 + 16
    caption(draw, width, y + 8, f"AssistIQ Baseline A · {name}", f_cap)
    path = OUT / f"{name}.png"
    img.crop((0, 0, width, min(h, y + 50))).save(path, dpi=(300, 300))
    print("Wrote", path)


def main():
    stack(
        "Figure_A_Intent_Detection",
        "Figure A — Intent Detection",
        [
            ("p", "User message x"),
            ("p", "Lowercase / normalize ℓ(x)"),
            ("p", "Scan keyword groups in order O"),
            ("d", "∃ w ∈ K_I with w ⊆ ℓ(x) ?"),
            ("p", "Yes → first matching intent I*"),
            ("d", "No match: “?” ∈ x ?"),
            ("p", "Yes → GENERAL_QUERY\nNo → KNOWLEDGE_QUERY"),
            ("d", "I*=KNOWLEDGE_QUERY &\noptional model?"),
            ("w", "Lightweight hit-rate heuristic\n(NOT trained SVM/logreg)"),
            ("p", "Output intent I*"),
        ],
    )

    stack(
        "Figure_B_Request_Routing",
        "Figure B — Deterministic Routing",
        [
            ("p", "Detected intent c"),
            ("m", "r(c) = INTENT_ROUTE_MAP[c]"),
            ("p", "knowledge/general → retrieve_context"),
            ("p", "ticket_* → retrieve_ticket_context"),
            ("p", "password_reset → start_password_reset"),
            ("p", "software_access → start_it_request"),
            ("p", "human_escalation → escalate"),
            ("p", "unsupported / unknown → handle_unsupported"),
            ("p", "Output: workflow node\n(dictionary routing, not ML)"),
        ],
        step_h=44,
    )

    stack(
        "Figure_C_Hash_Embedding",
        "Figure C — Hash Embedding (hash-v1)",
        [
            ("p", "Normalized query text"),
            ("p", "Whitespace tokenize"),
            ("m", "For token t: SHA-256(t)"),
            ("m", "j=(b+i) mod d\nv_j ← v_j + 1 + b/255\nd=384"),
            ("m", "e = v / ∥v∥₂  (∥v∥₂≠0)"),
            ("p", "Output: 384-D hash-v1 vector\n(deterministic, not trained)"),
        ],
        step_h=52,
    )

    stack(
        "Figure_D_Retrieval_Confidence",
        "Figure D — Retrieval + Confidence",
        [
            ("p", "Query embedding e"),
            ("p", "Chroma HNSW · cosine distance"),
            ("p", "Filter: published only"),
            ("m", "Top-k retrieval · k=3"),
            ("m", "s_i = max(0, 1 − d_i)"),
            ("p", "Postgres chunk/document validate"),
            ("p", "s_top = first citation score"),
            ("d", "empty / missing s_top?"),
            ("p", "→ NO_EVIDENCE"),
            ("d", "s_top ≥ 0.65 ?"),
            ("p", "→ HIGH_CONFIDENCE"),
            ("d", "s_top ≥ 0.35 ?"),
            ("p", "→ LOW else NO_EVIDENCE"),
            ("w", "NO_EVIDENCE on knowledge/general\n→ grounding warning (no auto-escalate)"),
        ],
        width=760,
        step_h=42,
        gap=18,
    )

    stack(
        "Figure_E_RAG_Generation",
        "Figure E — RAG Response Generation",
        [
            ("p", "User question Q"),
            ("p", "History: last 6 × ≤400 chars"),
            ("p", "KB citations: ≤5 × ≤500 chars"),
            ("p", "Ticket context if applicable"),
            ("m", "RAG prompt\nretrieved text = DATA"),
            ("p", "Selected generation LLM"),
            ("p", "Generate answer"),
            ("p", "Citation validation"),
            ("p", "Confidence check"),
            ("p", "Final response\n(not hallucination-free)"),
        ],
        step_h=44,
    )

    stack(
        "Figure_F_IT_Decision",
        "Figure F — IT / Software Access Decision",
        [
            ("p", "Software / access request"),
            ("p", "Entity extraction + catalog match"),
            ("m", "conf=0.9 match / 0.35 else\nPERMISSION capped at 0.6"),
            ("d", "Critical keywords?"),
            ("p", "Yes → ESCALATE"),
            ("d", "PERMISSION / privileged?"),
            ("p", "Yes → ESCALATE"),
            ("d", "Catalog matched & enabled?"),
            ("p", "No → DENY"),
            ("d", "Catalog CRITICAL?"),
            ("p", "Yes → ESCALATE"),
            ("d", "HIGH / approval / MEDIUM?"),
            ("p", "Yes → APPROVAL_REQUIRED"),
            ("p", "Else ALLOW (LOW)"),
            ("w", "Mock execution only\nNo real install / access grant"),
        ],
        width=760,
        step_h=40,
        gap=16,
    )

    stack(
        "Figure_G_Password_Reset",
        "Figure G — Password Reset Decision",
        [
            ("p", "Password reset request"),
            ("p", "Create request · TTL = 30 min"),
            ("d", "Email = actor email?"),
            ("p", "No → FAILED / escalate path"),
            ("d", "Suspicious claims?"),
            ("p", "Yes → REQUIRES_ESCALATION"),
            ("p", "Else VERIFIED"),
            ("p", "Risk assessment\nself→LOW; suspicious/other→HIGH/CRIT"),
            ("d", "Employee → other user?"),
            ("p", "Yes → DENY"),
            ("d", "FAILED & high risk?"),
            ("p", "Yes → ESCALATE; FAILED→DENY"),
            ("d", "Not VERIFIED or HIGH/CRIT risk?"),
            ("p", "Yes → ESCALATE"),
            ("p", "Else REQUIRE_CONFIRMATION"),
            ("p", "Explicit confirmation"),
            ("w", "Mock IAM only\nNo live password change"),
        ],
        width=760,
        step_h=40,
        gap=16,
    )


if __name__ == "__main__":
    main()
