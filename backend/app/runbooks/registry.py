"""Static allow-listed runbook registry."""

from __future__ import annotations

from app.runbooks.base import (
    AccessGrantRunbook,
    BaseRunbook,
    PrivilegedAccessRunbook,
    SoftwareInstallRunbook,
    UnknownRunbookError,
    RunbookDisabledError,
)

_RUNBOOKS: dict[str, BaseRunbook] = {
    "software.install.vscode": SoftwareInstallRunbook("software.install.vscode", "vscode"),
    "software.install.python": SoftwareInstallRunbook("software.install.python", "python"),
    "software.install.git": SoftwareInstallRunbook("software.install.git", "git"),
    "software.install.7zip": SoftwareInstallRunbook("software.install.7zip", "7zip"),
    "software.install.visio": SoftwareInstallRunbook("software.install.visio", "visio"),
    "software.install.office": SoftwareInstallRunbook("software.install.office", "office"),
    "access.request.jira": AccessGrantRunbook("access.request.jira", "jira"),
    "access.request.confluence": AccessGrantRunbook("access.request.confluence", "confluence"),
    "access.request.finance_shared_drive": AccessGrantRunbook(
        "access.request.finance_shared_drive", "finance_shared_drive"
    ),
    "access.request.monitoring_dashboard": AccessGrantRunbook(
        "access.request.monitoring_dashboard", "monitoring_dashboard"
    ),
    "access.privileged.blocked": PrivilegedAccessRunbook(),
}

_DISABLED: set[str] = set()


def get_runbook(runbook_id: str) -> BaseRunbook:
    if runbook_id not in _RUNBOOKS:
        raise UnknownRunbookError(f"Unknown runbook: {runbook_id}")
    if runbook_id in _DISABLED:
        raise RunbookDisabledError(f"Runbook is disabled: {runbook_id}")
    return _RUNBOOKS[runbook_id]


def list_runbook_ids() -> list[str]:
    return list(_RUNBOOKS.keys())


def disable_runbook(runbook_id: str) -> None:
    _DISABLED.add(runbook_id)


def enable_runbook(runbook_id: str) -> None:
    _DISABLED.discard(runbook_id)


def reset_runbook_registry() -> None:
    _DISABLED.clear()
