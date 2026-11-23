"""Build synthetic AssistIQ-labelled research datasets (explicitly synthetic)."""

from __future__ import annotations

import json
import random
from pathlib import Path

from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
SEED = 42

# Templates: (intent, texts). Mix of keyword-aligned and paraphrase/low-overlap items.
TEMPLATES: dict[str, list[str]] = {
    "human_escalation": [
        "I want to speak to a human agent",
        "Please escalate this to a representative",
        "Can I talk to a real person please",
        "Connect me with support staff now",
        "This needs a live agent not a bot",
        "Transfer me to someone on the helpdesk team",
        "I refuse chatbot answers get me a human",
        "Escalate to Tier 2 specialist",
        "I need to speak with an IT representative urgently",
        "Put me through to an agent",
        "Human assistance required for this issue",
        "Stop automated replies and escalate",
        "May I please speak to an operator",
        "Route this conversation to a person",
        "I already tried self-service I need a human",
        "Get me a desk agent on the phone",
        "Representative please this is urgent",
        "Escalate my case to management",
        "I want human review of my account issue",
        "Speak to support lead now",
    ],
    "password_reset_request": [
        "I need a password reset",
        "Please reset my password",
        "I forgot my password and cannot login",
        "How do I change password for my account",
        "Reset my corporate password",
        "My login password expired help me reset",
        "I cannot remember my credentials",
        "Unlock my account I forgot the passcode",
        "Initiate password recovery for my email",
        "Change password for SSO account",
        "Password reset portal is not working",
        "I need to renew my expired login secret",
        "Help me regain access I lost my password",
        "Reset credentials for employee portal",
        "Forgot password link please",
        "My password must be changed immediately",
        "Unable to sign in after forgetting password",
        "Please start the password reset workflow",
        "I need to set a new password",
        "Reset AD password for my user id",
    ],
    "software_access_request": [
        "I need Visual Studio Code installed",
        "Please install python on my laptop",
        "I need access to Jira",
        "Give me access to Confluence",
        "Install git for development work",
        "Request access to finance shared drive",
        "I need Microsoft Office installed",
        "Install 7-Zip on my machine",
        "Need elevated access for installer",
        "Please grant monitoring dashboard access",
        "Software access request for Visio",
        "I need vs code for backend development",
        "Install Microsoft Visio for diagrams",
        "Request software install of Python 3",
        "Need access to the project Confluence space",
        "Open an access request for Jira project XYZ",
        "I require git tools installed today",
        "Please provision Office suite",
        "Need vscode and python installed",
        "Admin privileges required to install a package",
        "I want confluence and jira entitlements",
        "Can you install 7zip for archives",
        "Shared drive access for finance folder",
        "Monitoring dashboard permission please",
        "Install software from approved catalog",
    ],
    "ticket_creation_request": [
        "Please create ticket for printer failure",
        "I want to open ticket about wifi outage",
        "Submit ticket for laptop battery issue",
        "New ticket needed for email delivery failure",
        "Create a support ticket for me",
        "Open ticket regarding broken keyboard",
        "Please file a new ticket for VPN dropouts",
        "Submit a ticket about slow laptop",
        "I need to create ticket for monitor flicker",
        "Open a ticket for docking station problem",
        "New ticket: cannot print to floor printer",
        "Create ticket - headset not working",
        "Submit ticket for application crash",
        "Please open ticket for missing mailbox",
        "I want to raise a ticket for hardware fault",
        "Create IT ticket for desk phone issue",
        "Open ticket for access badge reader",
        "New ticket about Teams audio problems",
        "Submit ticket for failed software update",
        "Create ticket documenting the outage",
    ],
    "ticket_query": [
        "What is my ticket status",
        "Show me my ticket number TCK-102",
        "Update on ticket #4451 please",
        "Where is my open ticket",
        "Check status of my tickets",
        "Has my ticket been assigned",
        "Ticket status for my laptop request",
        "Look up my ticket by number",
        "Is my ticket still pending",
        "Progress on my earlier ticket",
        "Show open tickets for my account",
        "My ticket was updated yesterday what changed",
        "Tell me the status of ticket 8890",
        "Did the agent close my ticket",
        "Ticket number and current state please",
        "Follow up on my existing ticket",
        "When will my ticket be resolved",
        "List my recent tickets",
        "Ticket #1201 status check",
        "Any update on the ticket I opened",
    ],
    "knowledge_query": [
        "How do I connect to the corporate VPN",
        "How to join office wifi network",
        "Guide for resetting MFA token",
        "What is the password policy length",
        "Procedure for requesting a loaner laptop",
        "How do I configure Outlook on Windows",
        "VPN client installation guide",
        "Wifi troubleshooting steps for Windows",
        "Company policy for USB storage",
        "How to set up email on mobile",
        "Procedure to report phishing",
        "How do I map a network drive",
        "Guide to using the knowledge base search",
        "How to enable MFA on my account",
        "VPN split tunneling policy explanation",
        "How do I clear browser cache for SSO",
        "Steps to connect printer by IP",
        "How to check disk space on Windows",
        "Wifi SSID and connection guide",
        "How do I update the VPN profile",
        "Explain the remote work network procedure",
        "Documented steps for certificate renewal",
        "How to troubleshoot DNS resolution",
        "Policy for screen lock timeout",
        "How do I access the intranet portal",
    ],
    "general_query": [
        "Is the helpdesk available today?",
        "What are your support hours?",
        "Can AssistIQ help with IT questions?",
        "Who owns the corporate laptop fleet?",
        "Is there weekend support coverage?",
        "What channels can I use for IT help?",
        "Are chat responses saved?",
        "Do you support macOS devices?",
        "Is remote support available?",
        "What information should I include in a request?",
        "Can agents see my chat history?",
        "Is this service for employees only?",
        "How long do responses usually take?",
        "Are there fees for IT support?",
        "Which regions does IT cover?",
        "Can I escalate after hours?",
        "Is knowledge base public?",
        "Do you store my messages?",
        "Who can approve software requests?",
        "Is MFA mandatory for everyone?",
    ],
    "unsupported": [
        "Write me a poem about servers",
        "What is the weather in Mumbai",
        "Translate this menu into French",
        "Recommend a movie for tonight",
        "Solve this calculus homework",
        "Generate a marketing slogan",
        "Tell me a joke about databases",
        "Plan my vacation itinerary",
        "What is 2 plus 2 in binary poetry form",
        "Cook a recipe for pasta",
        "Draft a love letter",
        "Speculate about stock tips",
        "Create a fantasy character sheet",
        "Who will win the cricket match",
        "Summarize yesterday's football game",
        "Invent a startup idea unrelated to IT",
        "Write SQL for a dating app schema joke",
        "Generate meme captions",
        "Advise on personal relationship conflict",
        "Compose bedtime story for kids",
    ],
}


def expand(rng: random.Random) -> list[dict]:
    rows: list[dict] = []
    uid = 0
    for intent, texts in TEMPLATES.items():
        for text in texts:
            uid += 1
            # paraphrase-ish variants: light edits
            variants = [text]
            if intent not in {"unsupported"}:
                variants.append(text.replace("Please ", "").replace("I need ", "I require "))
                variants.append(text + " thanks")
            for v in variants:
                v = " ".join(v.split())
                if not v:
                    continue
                stratum = "keyword_heavy"
                # mark low-overlap paraphrases for analysis
                if intent == "password_reset_request" and "password" not in v.lower() and "reset" not in v.lower():
                    stratum = "paraphrase"
                if intent == "human_escalation" and not any(
                    k in v.lower() for k in ("human", "agent", "escalate", "representative", "speak to")
                ):
                    stratum = "paraphrase"
                rows.append(
                    {
                        "id": f"syn-{uid:04d}-{abs(hash(v)) % 10000}",
                        "text": v,
                        "intent": intent,
                        "stratum": stratum,
                        "source": "synthetic_assistiq_templates",
                    }
                )
                uid += 1
    rng.shuffle(rows)
    # dedupe by text
    seen = set()
    unique = []
    for r in rows:
        key = r["text"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return unique


def split_rows(rows: list[dict], seed: int = SEED):
    labels = [r["intent"] for r in rows]
    train, temp = train_test_split(rows, test_size=0.30, random_state=seed, stratify=labels)
    labels_temp = [r["intent"] for r in temp]
    val, test = train_test_split(temp, test_size=0.50, random_state=seed, stratify=labels_temp)
    return train, val, test


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def build_routing(rows: list[dict]) -> list[dict]:
    from src.baseline_a_logic import INTENT_ROUTE_MAP

    out = []
    for r in rows:
        route = INTENT_ROUTE_MAP.get(r["intent"], "handle_unsupported")
        out.append(
            {
                **r,
                "gold_route": route,
                "false_automation_sensitive": route
                in {"start_it_request", "start_password_reset"},
            }
        )
    return out


def build_kb_and_qrels(rng: random.Random):
    docs = [
        {
            "doc_id": "kb-vpn",
            "title": "Corporate VPN Connection Guide",
            "content": (
                "To connect to the corporate VPN install the approved client, open the profile "
                "named CorpVPN, authenticate with SSO, and confirm the tunnel status is Connected. "
                "If the VPN drops, restart the client and check network DNS settings."
            ),
        },
        {
            "doc_id": "kb-wifi",
            "title": "Office Wi-Fi Troubleshooting",
            "content": (
                "Join the corporate wifi SSID CorpSecure using your employee credentials. "
                "Forget the network and reconnect if authentication fails. Disable random MAC "
                "addressing on Windows and renew the DHCP lease."
            ),
        },
        {
            "doc_id": "kb-password-policy",
            "title": "Password Policy",
            "content": (
                "Passwords must be at least 12 characters and include mixed case, a number, and "
                "a symbol. Employees must not share passwords. Expired passwords require a "
                "self-service reset after identity verification."
            ),
        },
        {
            "doc_id": "kb-mfa",
            "title": "MFA Enrollment Guide",
            "content": (
                "Enable multi-factor authentication in the security portal. Register an authenticator "
                "app, verify a one-time code, and store backup codes securely. Lost MFA devices "
                "require identity verification before reset."
            ),
        },
        {
            "doc_id": "kb-printer",
            "title": "Network Printer Setup",
            "content": (
                "Add a printer by IP using the standard TCP/IP port. Install the approved driver "
                "from the software catalog. Print a test page and verify queue status."
            ),
        },
        {
            "doc_id": "kb-email",
            "title": "Outlook Configuration",
            "content": (
                "Configure Outlook with modern authentication. Sign in with corporate email, "
                "allow MFA prompts, and sync folders. Clear credential manager entries if "
                "repeated login loops occur."
            ),
        },
        {
            "doc_id": "kb-phishing",
            "title": "Report Phishing Procedure",
            "content": (
                "Do not click suspicious links. Forward the message to phishing@company.example "
                "and then delete it. Contact the security team if credentials were entered."
            ),
        },
        {
            "doc_id": "kb-loaner",
            "title": "Loaner Laptop Procedure",
            "content": (
                "Request a loaner laptop through the hardware request form. Collect from the IT "
                "desk with employee ID. Return within the approved loan period."
            ),
        },
        {
            "doc_id": "kb-unrelated",
            "title": "Cafeteria Menu Policy",
            "content": (
                "The cafeteria publishes weekly menus. Dietary requests go to facilities. "
                "This document is unrelated to networking or password troubleshooting."
            ),
        },
        {
            "doc_id": "kb-git",
            "title": "Approved Git Client Install",
            "content": (
                "Git is available from the approved software catalog. Request installation "
                "through IT Requests for low-risk catalog items. Do not download unsigned installers."
            ),
        },
    ]

    # one chunk per doc for research corpus
    chunks = []
    for d in docs:
        chunks.append(
            {
                "chunk_id": f"{d['doc_id']}-c0",
                "doc_id": d["doc_id"],
                "title": d["title"],
                "content": d["content"],
            }
        )

    qrels_queries = [
        ("q1", "How do I connect to the corporate VPN", ["kb-vpn-c0"], "lexical"),
        ("q2", "VPN tunnel keeps dropping what should I check", ["kb-vpn-c0"], "paraphrase"),
        ("q3", "How to join office wifi network", ["kb-wifi-c0"], "lexical"),
        ("q4", "Cannot authenticate to wireless SSID at work", ["kb-wifi-c0"], "paraphrase"),
        ("q5", "What is the password policy length", ["kb-password-policy-c0"], "lexical"),
        ("q6", "Rules for creating a strong login secret", ["kb-password-policy-c0"], "paraphrase"),
        ("q7", "How to enable MFA on my account", ["kb-mfa-c0"], "lexical"),
        ("q8", "Authenticator app enrollment steps", ["kb-mfa-c0"], "paraphrase"),
        ("q9", "Steps to connect printer by IP", ["kb-printer-c0"], "lexical"),
        ("q10", "Add floor printer using TCP port", ["kb-printer-c0"], "paraphrase"),
        ("q11", "How to configure Outlook on Windows", ["kb-email-c0"], "lexical"),
        ("q12", "Outlook keeps asking for credentials", ["kb-email-c0"], "paraphrase"),
        ("q13", "Procedure to report phishing", ["kb-phishing-c0"], "lexical"),
        ("q14", "Suspicious email with link what do I do", ["kb-phishing-c0"], "paraphrase"),
        ("q15", "Procedure for requesting a loaner laptop", ["kb-loaner-c0"], "lexical"),
        ("q16", "I need a temporary laptop while mine is repaired", ["kb-loaner-c0"], "paraphrase"),
        ("q17", "Approved way to install git", ["kb-git-c0"], "lexical"),
        ("q18", "How developers get version control tools installed", ["kb-git-c0"], "paraphrase"),
        ("q19", "Corporate VPN SSO profile name", ["kb-vpn-c0"], "lexical"),
        ("q20", "Remote access client configuration guide", ["kb-vpn-c0"], "paraphrase"),
        ("q21", "Wifi troubleshooting after failed login", ["kb-wifi-c0"], "paraphrase"),
        ("q22", "Minimum characters required for passwords", ["kb-password-policy-c0"], "paraphrase"),
        ("q23", "Lost phone MFA recovery", ["kb-mfa-c0"], "paraphrase"),
        ("q24", "Install driver for network printer", ["kb-printer-c0"], "paraphrase"),
        ("q25", "Modern authentication for mail client", ["kb-email-c0"], "paraphrase"),
        ("q26", "Forward phishing to security mailbox", ["kb-phishing-c0"], "lexical"),
        ("q27", "Collect loaner from IT desk", ["kb-loaner-c0"], "lexical"),
        ("q28", "Do not use unsigned git installers", ["kb-git-c0"], "lexical"),
        ("q29", "Check VPN Connected status", ["kb-vpn-c0"], "lexical"),
        ("q30", "Disable random MAC for corporate wireless", ["kb-wifi-c0"], "lexical"),
    ]

    queries = []
    qrels = []
    for qid, text, relevant, stratum in qrels_queries:
        queries.append({"query_id": qid, "text": text, "stratum": stratum})
        for cid in relevant:
            qrels.append({"query_id": qid, "chunk_id": cid, "relevance": 1})

    return chunks, queries, qrels


def main():
    rng = random.Random(SEED)
    rows = expand(rng)
    train, val, test = split_rows(rows, SEED)

    intent_dir = ROOT / "datasets" / "intent"
    write_jsonl(intent_dir / "train.jsonl", train)
    write_jsonl(intent_dir / "val.jsonl", val)
    write_jsonl(intent_dir / "test.jsonl", test)
    write_jsonl(intent_dir / "all.jsonl", rows)

    routing_dir = ROOT / "datasets" / "routing"
    write_jsonl(routing_dir / "train.jsonl", build_routing(train))
    write_jsonl(routing_dir / "val.jsonl", build_routing(val))
    write_jsonl(routing_dir / "test.jsonl", build_routing(test))

    chunks, queries, qrels = build_kb_and_qrels(rng)
    kb_dir = ROOT / "datasets" / "kb"
    qrels_dir = ROOT / "datasets" / "qrels"
    write_jsonl(kb_dir / "chunks.jsonl", chunks)
    write_jsonl(qrels_dir / "queries.jsonl", queries)
    write_jsonl(qrels_dir / "qrels.jsonl", qrels)

    meta = {
        "dataset_type": "synthetic_research",
        "seed": SEED,
        "intent_counts": {k: sum(1 for r in rows if r["intent"] == k) for k in TEMPLATES},
        "n_intent": len(rows),
        "n_train": len(train),
        "n_val": len(val),
        "n_test": len(test),
        "n_chunks": len(chunks),
        "n_queries": len(queries),
        "warning": (
            "SYNTHETIC labels generated for reproducible AssistIQ-shaped evaluation. "
            "Not production user data. Not a public IT ticket corpus."
        ),
    }
    (ROOT / "datasets" / "DATASET_CARD.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(ROOT))
    main()
