"""Allow-listed IAM adapters. Phase 8 enables mock simulation only."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID, uuid4

FORBIDDEN_KEYS = {
    "command",
    "shell",
    "powershell",
    "bash",
    "cmd",
    "sql",
    "script",
    "password",
    "token",
    "secret",
    "credential",
}


class IAMAdapterError(Exception):
    pass


class IAMAdapter(ABC):
    name: str
    rollback_supported: bool = False

    @abstractmethod
    async def reset_password(self, *, target_user_id: UUID, request_id: UUID, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def validate_reset(self, *, target_user_id: UUID, execution_result: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    async def rollback_reset(self, *, target_user_id: UUID, execution_result: dict[str, Any]) -> dict[str, Any]:
        return {
            "adapter": self.name,
            "simulated": True,
            "rolled_back": False,
            "rollback_supported": False,
            "message": "Password reset rollback is not supported.",
        }


class MockIAMAdapter(IAMAdapter):
    """Simulates a password reset. Never changes User.password_hash or any IAM system."""

    name = "mock"
    rollback_supported = False

    async def reset_password(self, *, target_user_id: UUID, request_id: UUID, context: dict[str, Any]) -> dict[str, Any]:
        extra = context.get("execution_params") or {}
        if not isinstance(extra, dict):
            raise IAMAdapterError("execution_params must be a mapping")
        for key in extra:
            if str(key).lower() in FORBIDDEN_KEYS:
                raise IAMAdapterError("Arbitrary IAM execution parameters are not allowed")
        if context.get("password") or context.get("token") or context.get("secret"):
            raise IAMAdapterError("Secrets must not be supplied to the IAM adapter")

        force_failure = bool(context.get("force_failure"))
        operation_id = str(uuid4())
        return {
            "adapter": self.name,
            "simulated": True,
            "success": not force_failure,
            "operation_id": operation_id,
            "target_user_id": str(target_user_id),
            "request_id": str(request_id),
            "message": (
                "Password reset simulation completed successfully."
                if not force_failure
                else "Password reset simulation failed."
            ),
        }

    async def validate_reset(self, *, target_user_id: UUID, execution_result: dict[str, Any]) -> dict[str, Any]:
        if execution_result.get("adapter") != self.name:
            return {"passed": False, "reason": "Only the mock IAM adapter is enabled"}
        if not execution_result.get("simulated"):
            return {"passed": False, "reason": "Non-simulated IAM execution is not permitted"}
        if execution_result.get("target_user_id") != str(target_user_id):
            return {"passed": False, "reason": "Target user mismatch"}
        if not execution_result.get("operation_id"):
            return {"passed": False, "reason": "Missing simulated operation id"}
        if not execution_result.get("success"):
            return {"passed": False, "reason": "Simulated IAM operation reported failure"}
        return {"passed": True, "reason": "Simulated IAM acknowledgement matched the expected state"}


class FutureIAMAdapter(IAMAdapter):
    name = "future_iam"

    async def reset_password(self, *, target_user_id: UUID, request_id: UUID, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Real IAM password changes are not enabled in Phase 8")

    async def validate_reset(self, *, target_user_id: UUID, execution_result: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("Real IAM password changes are not enabled in Phase 8")


_adapter: IAMAdapter | None = None


def get_iam_adapter() -> IAMAdapter:
    global _adapter
    if _adapter is None:
        _adapter = MockIAMAdapter()
    if _adapter.name != "mock":
        raise IAMAdapterError("Only MockIAMAdapter is enabled in Phase 8")
    return _adapter


def set_iam_adapter(adapter: IAMAdapter) -> None:
    global _adapter
    _adapter = adapter


def reset_iam_adapter() -> None:
    global _adapter
    _adapter = None
