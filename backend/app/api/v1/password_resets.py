from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rate_limit import rate_limit
from app.iam.adapter import IAMAdapterError
from app.models.user import User
from app.schemas.password_reset import (
    PasswordResetConfirmRequest,
    PasswordResetCreate,
    PasswordResetEscalateRequest,
    PasswordResetListItem,
    PasswordResetListResponse,
    PasswordResetResponse,
    PasswordResetVerifyRequest,
)
from app.services.password_reset_service import (
    PasswordResetAccessDeniedError,
    PasswordResetNotFoundError,
    PasswordResetService,
    PasswordResetValidationError,
    get_password_reset_service,
)

router = APIRouter(prefix="/password-resets")


def _handle(exc: Exception) -> HTTPException:
    if isinstance(exc, PasswordResetNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, PasswordResetAccessDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, (PasswordResetValidationError, IAMAdapterError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")


@router.post("", response_model=PasswordResetResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit("password_reset"))])
async def create_password_reset(
    payload: PasswordResetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PasswordResetService = Depends(get_password_reset_service),
) -> PasswordResetResponse:
    try:
        request = await service.create_request(
            db,
            actor=current_user,
            target_user_id=payload.target_user_id,
            message=payload.message,
        )
    except Exception as exc:
        raise _handle(exc) from exc
    return PasswordResetResponse.model_validate(request)


@router.get("", response_model=PasswordResetListResponse)
async def list_password_resets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PasswordResetService = Depends(get_password_reset_service),
) -> PasswordResetListResponse:
    items = await service.list_requests(db, actor=current_user)
    return PasswordResetListResponse(
        items=[PasswordResetListItem.model_validate(item) for item in items],
        total=len(items),
    )


@router.get("/{request_id}", response_model=PasswordResetResponse)
async def get_password_reset(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PasswordResetService = Depends(get_password_reset_service),
) -> PasswordResetResponse:
    try:
        request = await service.get_request(db, actor=current_user, request_id=request_id)
    except Exception as exc:
        raise _handle(exc) from exc
    return PasswordResetResponse.model_validate(request)


@router.post("/{request_id}/verify", response_model=PasswordResetResponse, dependencies=[Depends(rate_limit("password_reset"))])
async def verify_password_reset(
    request_id: UUID,
    payload: PasswordResetVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PasswordResetService = Depends(get_password_reset_service),
) -> PasswordResetResponse:
    try:
        request = await service.verify(
            db, actor=current_user, request_id=request_id, email=payload.email
        )
    except Exception as exc:
        raise _handle(exc) from exc
    return PasswordResetResponse.model_validate(request)


@router.post("/{request_id}/confirm", response_model=PasswordResetResponse, dependencies=[Depends(rate_limit("password_reset"))])
async def confirm_password_reset(
    request_id: UUID,
    payload: PasswordResetConfirmRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PasswordResetService = Depends(get_password_reset_service),
) -> PasswordResetResponse:
    try:
        request = await service.confirm(db, actor=current_user, request_id=request_id)
    except Exception as exc:
        raise _handle(exc) from exc
    return PasswordResetResponse.model_validate(request)


@router.post("/{request_id}/escalate", response_model=PasswordResetResponse)
async def escalate_password_reset(
    request_id: UUID,
    payload: PasswordResetEscalateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PasswordResetService = Depends(get_password_reset_service),
) -> PasswordResetResponse:
    body = payload or PasswordResetEscalateRequest()
    try:
        request = await service.escalate(
            db, actor=current_user, request_id=request_id, reason=body.reason
        )
    except Exception as exc:
        raise _handle(exc) from exc
    return PasswordResetResponse.model_validate(request)


@router.post("/{request_id}/reject", response_model=PasswordResetResponse)
async def reject_password_reset(
    request_id: UUID,
    payload: PasswordResetEscalateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: PasswordResetService = Depends(get_password_reset_service),
) -> PasswordResetResponse:
    body = payload or PasswordResetEscalateRequest()
    try:
        request = await service.reject(
            db, actor=current_user, request_id=request_id, reason=body.reason
        )
    except Exception as exc:
        raise _handle(exc) from exc
    return PasswordResetResponse.model_validate(request)
