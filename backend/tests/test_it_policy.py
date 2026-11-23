"""Isolated IT policy engine tests. No Neon, no adapters that mutate systems."""

import pytest

from app.models.it_request import ITPolicyDecision, ITRequestType, ITRiskLevel
from app.services.policy_service import PolicyInput, evaluate_policy
from app.execution.adapter import MockExecutionAdapter


def _input(**overrides) -> PolicyInput:
    values = dict(
        request_type=ITRequestType.SOFTWARE,
        user_message="I need VS Code installed",
        catalog_matched=True,
        catalog_enabled=True,
        catalog_risk=ITRiskLevel.LOW,
        catalog_approval_required=False,
        resource="vscode",
    )
    values.update(overrides)
    return PolicyInput(**values)


def test_catalog_software_is_allowed():
    result = evaluate_policy(_input())
    assert result.decision == ITPolicyDecision.ALLOW
    assert result.approval_required is False


def test_unknown_catalog_is_denied():
    result = evaluate_policy(_input(catalog_matched=False, resource="unknown-tool"))
    assert result.decision == ITPolicyDecision.DENY


def test_privileged_access_requires_human():
    result = evaluate_policy(
        _input(
            request_type=ITRequestType.PERMISSION,
            user_message="I need admin privileges on the finance shared drive",
            catalog_matched=True,
            catalog_risk=ITRiskLevel.HIGH,
            catalog_approval_required=True,
            resource="finance-share",
        )
    )
    assert result.decision == ITPolicyDecision.ESCALATE
    assert result.approval_required is True


def test_critical_keywords_escalate():
    result = evaluate_policy(_input(user_message="Please grant domain admin"))
    assert result.decision == ITPolicyDecision.ESCALATE
    assert result.risk_level == ITRiskLevel.CRITICAL


@pytest.mark.asyncio
async def test_mock_execution_is_labeled_simulated():
    adapter = MockExecutionAdapter()
    result = await adapter.execute(
        runbook_id="software.vscode",
        expected={"installed": True},
        context={},
    )
    assert result["simulated"] is True
    assert result["adapter"] == "mock"
    assert result["success"] is True


@pytest.mark.asyncio
async def test_mock_execution_failure_is_honest():
    adapter = MockExecutionAdapter()
    result = await adapter.execute(
        runbook_id="software.vscode",
        expected={"installed": True},
        context={"force_failure": True},
    )
    assert result["simulated"] is True
    assert result["success"] is False
