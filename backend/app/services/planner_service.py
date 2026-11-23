"""Select allow-listed runbooks only. Never invent commands or runbooks."""

from __future__ import annotations

from app.models.it_request import ITRequestType
from app.runbooks.base import RunbookValidationError, UnknownRunbookError
from app.runbooks.registry import get_runbook


ALLOWED_STEPS = {
    "verify_request",
    "verify_catalog_entry",
    "prepare_action",
    "prepare_installation",
    "execute_allowlisted_action",
    "validate_result",
    "validate_installation",
}


def build_plan(
    *,
    runbook_id: str | None,
    request_type: ITRequestType,
    resource: str,
    catalog_matched: bool,
) -> dict:
    if request_type == ITRequestType.PERMISSION:
        raise RunbookValidationError("Privileged permission requests have no executable runbook")
    if not catalog_matched or not runbook_id:
        raise UnknownRunbookError("No allow-listed runbook mapped for this request")

    handler = get_runbook(runbook_id)
    plan = handler.plan({"runbook_id": runbook_id, "resource": resource, "request_type": request_type.value})
    for step in plan.get("steps", []):
        if step not in ALLOWED_STEPS:
            raise RunbookValidationError("Planner produced a non-allow-listed step")
    return plan
