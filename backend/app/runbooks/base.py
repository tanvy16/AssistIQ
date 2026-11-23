"""Allow-listed runbook handlers. Never execute arbitrary commands."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


FORBIDDEN_KEYS = {
    "command",
    "shell",
    "powershell",
    "bash",
    "cmd",
    "sql",
    "script",
    "url",
    "payload",
}


class RunbookError(Exception):
    pass


class RunbookDisabledError(RunbookError):
    pass


class UnknownRunbookError(RunbookError):
    pass


class RunbookValidationError(RunbookError):
    pass


class BaseRunbook(ABC):
    runbook_id: str
    action_type: str
    rollback_supported: bool = True

    def validate(self, context: dict[str, Any]) -> None:
        self._reject_arbitrary_execution(context)
        if context.get("runbook_id") != self.runbook_id:
            raise RunbookValidationError("Runbook id mismatch")

    def plan(self, context: dict[str, Any]) -> dict[str, Any]:
        self.validate(context)
        return {
            "runbook_id": self.runbook_id,
            "action_type": self.action_type,
            "steps": [
                "verify_request",
                "verify_catalog_entry",
                "prepare_action",
                "execute_allowlisted_action",
                "validate_result",
            ],
            "resource": context.get("resource"),
            "simulated": True,
        }

    @abstractmethod
    def expected_result(self, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def _reject_arbitrary_execution(self, context: dict[str, Any]) -> None:
        extra = context.get("execution_params") or {}
        if not isinstance(extra, dict):
            raise RunbookValidationError("execution_params must be a mapping")
        for key in extra:
            if str(key).lower() in FORBIDDEN_KEYS:
                raise RunbookValidationError("Arbitrary execution parameters are not allowed")


class SoftwareInstallRunbook(BaseRunbook):
    action_type = "software_install"

    def __init__(self, runbook_id: str, package_identifier: str) -> None:
        self.runbook_id = runbook_id
        self.package_identifier = package_identifier

    def expected_result(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "action": "software_install",
            "package_identifier": self.package_identifier,
            "installed": True,
            "simulated": True,
            "resource": context.get("resource"),
        }


class AccessGrantRunbook(BaseRunbook):
    action_type = "access_grant"

    def __init__(self, runbook_id: str, resource_key: str) -> None:
        self.runbook_id = runbook_id
        self.resource_key = resource_key

    def expected_result(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "action": "access_grant",
            "resource_key": self.resource_key,
            "access_granted": True,
            "simulated": True,
            "resource": context.get("resource"),
        }


class PrivilegedAccessRunbook(BaseRunbook):
    """Privileged requests never auto-execute; rollback is unsupported."""

    action_type = "privileged_access"
    rollback_supported = False
    runbook_id = "access.privileged.blocked"

    def expected_result(self, context: dict[str, Any]) -> dict[str, Any]:
        raise RunbookValidationError("Privileged access cannot be executed automatically")
