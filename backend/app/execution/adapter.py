"""Replaceable execution adapters. Phase 7 enables mock only."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ExecutionAdapter(ABC):
    name: str

    @abstractmethod
    async def execute(self, *, runbook_id: str, expected: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def rollback(self, *, runbook_id: str, execution_result: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class MockExecutionAdapter(ExecutionAdapter):
    """Simulates allow-listed actions. Never touches host software or IAM."""

    name = "mock"

    async def execute(self, *, runbook_id: str, expected: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        force_failure = bool(context.get("force_failure"))
        return {
            "adapter": self.name,
            "simulated": True,
            "runbook_id": runbook_id,
            "success": not force_failure,
            "message": "Simulation completed successfully." if not force_failure else "Simulation failed.",
            "expected": expected,
            "installed": expected.get("installed") if not force_failure else False,
            "access_granted": expected.get("access_granted") if not force_failure else False,
        }

    async def rollback(self, *, runbook_id: str, execution_result: dict[str, Any]) -> dict[str, Any]:
        return {
            "adapter": self.name,
            "simulated": True,
            "runbook_id": runbook_id,
            "rolled_back": True,
            "message": "Simulation rollback completed.",
            "prior_result": {
                "success": execution_result.get("success"),
                "runbook_id": execution_result.get("runbook_id"),
            },
        }


class FutureSoftwareManagementAdapter(ExecutionAdapter):
    name = "software_management"

    async def execute(self, *, runbook_id: str, expected: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Real software management is not enabled in Phase 7")

    async def rollback(self, *, runbook_id: str, execution_result: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Real software management is not enabled in Phase 7")


class FutureIAMAdapter(ExecutionAdapter):
    name = "iam"

    async def execute(self, *, runbook_id: str, expected: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Real IAM changes are not enabled in Phase 7")

    async def rollback(self, *, runbook_id: str, execution_result: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Real IAM changes are not enabled in Phase 7")


_adapter: ExecutionAdapter | None = None


def get_execution_adapter() -> ExecutionAdapter:
    global _adapter
    if _adapter is None:
        _adapter = MockExecutionAdapter()
    return _adapter


def reset_execution_adapter() -> None:
    global _adapter
    _adapter = None
