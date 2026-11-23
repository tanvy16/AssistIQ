"""Experiment E: SIMULATED ITSM workflow evaluation (not a live user study)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.baseline_a_logic import evaluate_it_policy, password_policy  # noqa: E402

OUT = ROOT / "results" / "workflow"

# Documented manual baseline step counts / nominal minutes (research assumptions for simulation).
# These are SIMULATED timings from a written checklist, not observed wall-clock from humans.
MANUAL = {
    "low_risk_software": {"steps": 8, "minutes": 25},
    "approval_software": {"steps": 12, "minutes": 45},
    "privileged_escalate": {"steps": 10, "minutes": 40},
    "deny_uncatalogued": {"steps": 6, "minutes": 15},
    "password_success": {"steps": 7, "minutes": 20},
    "password_fail": {"steps": 5, "minutes": 12},
}


SCENARIOS = [
    {
        "id": "S1",
        "name": "low_risk_software",
        "kind": "it",
        "input": {
            "request_type": "SOFTWARE",
            "user_message": "Please install git for development",
            "catalog_matched": True,
            "catalog_enabled": True,
            "catalog_risk": "LOW",
            "catalog_approval_required": False,
        },
        "gold_decision": "ALLOW",
        "should_auto_execute_mock": True,
    },
    {
        "id": "S2",
        "name": "approval_software",
        "kind": "it",
        "input": {
            "request_type": "SOFTWARE",
            "user_message": "Install Microsoft Visio",
            "catalog_matched": True,
            "catalog_enabled": True,
            "catalog_risk": "MEDIUM",
            "catalog_approval_required": True,
        },
        "gold_decision": "APPROVAL_REQUIRED",
        "should_auto_execute_mock": False,
    },
    {
        "id": "S3",
        "name": "privileged_escalate",
        "kind": "it",
        "input": {
            "request_type": "PERMISSION",
            "user_message": "I need admin privileges and sudo on my laptop",
            "catalog_matched": True,
            "catalog_enabled": True,
            "catalog_risk": "HIGH",
            "catalog_approval_required": True,
        },
        "gold_decision": "ESCALATE",
        "should_auto_execute_mock": False,
    },
    {
        "id": "S4",
        "name": "deny_uncatalogued",
        "kind": "it",
        "input": {
            "request_type": "SOFTWARE",
            "user_message": "Install random pirate software xyz",
            "catalog_matched": False,
            "catalog_enabled": False,
            "catalog_risk": None,
            "catalog_approval_required": False,
        },
        "gold_decision": "DENY",
        "should_auto_execute_mock": False,
    },
    {
        "id": "S5",
        "name": "password_success",
        "kind": "password",
        "input": {
            "employee_other_user": False,
            "verification": "VERIFIED",
            "risk": "LOW",
        },
        "gold_decision": "REQUIRE_CONFIRMATION",
        "should_auto_execute_mock": False,  # needs explicit confirm then mock IAM
        "after_confirm": "MOCK_IAM",
    },
    {
        "id": "S6",
        "name": "password_fail",
        "kind": "password",
        "input": {
            "employee_other_user": False,
            "verification": "FAILED",
            "risk": "MEDIUM",
        },
        "gold_decision": "DENY",
        "should_auto_execute_mock": False,
    },
]


def run_scenario(sc: dict) -> dict:
    t0 = time.perf_counter()
    if sc["kind"] == "it":
        decision = evaluate_it_policy(**sc["input"])
        mock_executed = decision == "ALLOW"
        steps_auto = 3 if decision == "ALLOW" else 4
        minutes_auto = 2 if decision == "ALLOW" else 5
    else:
        decision = password_policy(**sc["input"])
        mock_executed = False
        if decision == "REQUIRE_CONFIRMATION":
            # simulated confirmation + mock IAM
            mock_executed = True
            steps_auto = 5
            minutes_auto = 4
        else:
            steps_auto = 3
            minutes_auto = 3
    elapsed_ms = (time.perf_counter() - t0) * 1000
    correct = decision == sc["gold_decision"]
    manual = MANUAL[sc["name"]]
    return {
        "id": sc["id"],
        "name": sc["name"],
        "decision": decision,
        "gold_decision": sc["gold_decision"],
        "decision_correct": correct,
        "mock_executed": mock_executed,
        "automated_steps": steps_auto,
        "manual_steps": manual["steps"],
        "automated_minutes_sim": minutes_auto,
        "manual_minutes_sim": manual["minutes"],
        "policy_latency_ms": elapsed_ms,
        "result_type": "SIMULATED",
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [run_scenario(sc) for sc in SCENARIOS]
    n = len(rows)
    completion = sum(1 for r in rows if r["decision_correct"]) / n
    # FCR definition for this simulation: task resolved without human escalation on first automated pass
    fcr = sum(1 for r in rows if r["decision_correct"] and r["decision"] != "ESCALATE") / n
    avg_auto_min = sum(r["automated_minutes_sim"] for r in rows) / n
    avg_manual_min = sum(r["manual_minutes_sim"] for r in rows) / n
    error_rate = 1.0 - completion
    escalation_ok = sum(
        1
        for r, sc in zip(rows, SCENARIOS)
        if (r["decision"] == "ESCALATE") == (sc["gold_decision"] == "ESCALATE")
    ) / n

    summary = {
        "result_type": "SIMULATED",
        "disclaimer": (
            "Workflow timings are simulated from documented checklist step counts, "
            "not measured live agent wall-clock. Mock IAM/execution only. "
            "Not a completed user study. Productivity gain must NOT be claimed as measured."
        ),
        "n_scenarios": n,
        "task_completion_rate": completion,
        "error_rate": error_rate,
        "fcr_sim_definition": "correct decision and not ESCALATE / n_scenarios",
        "fcr_simulated": fcr,
        "avg_automated_minutes_sim": avg_auto_min,
        "avg_manual_minutes_sim": avg_manual_min,
        "time_reduction_sim_ratio": (avg_manual_min - avg_auto_min) / avg_manual_min,
        "time_reduction_label": "SIMULATED_NOT_MEASURED_PRODUCTIVITY",
        "escalation_appropriateness": escalation_ok,
        "scenarios": rows,
    }
    (OUT / "metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "scenarios"}, indent=2))


if __name__ == "__main__":
    main()
