from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.rate_limit import rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.ai import (
    AIEvaluationCreateRequest,
    AIEvaluationResponse,
    AIInferRequest,
    AIInferResponse,
    AIInferUsageResponse,
    AIModelListResponse,
    AIModelResponse,
    AIModelUpdateRequest,
)
from app.services.ai_model_service import (
    AIModelDisabledError,
    AIModelNotFoundError,
    AIModelService,
    AIModelValidationError,
    get_ai_model_service,
)

router = APIRouter(prefix="/ai")


def _handle_ai_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, AIModelNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, AIModelDisabledError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, AIModelValidationError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")


@router.get("/models", response_model=AIModelListResponse)
async def list_ai_models(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AIModelService = Depends(get_ai_model_service),
) -> AIModelListResponse:
    include_disabled = current_user.role == UserRole.ADMIN
    models = await service.list_models(db, include_disabled=include_disabled)
    items = [AIModelResponse.model_validate(m) for m in models]
    return AIModelListResponse(items=items, total=len(items))


@router.get("/models/{model_id}", response_model=AIModelResponse)
async def get_ai_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AIModelService = Depends(get_ai_model_service),
) -> AIModelResponse:
    try:
        model = await service.get_model(
            db,
            model_id,
            allow_disabled=current_user.role == UserRole.ADMIN,
        )
    except Exception as exc:
        raise _handle_ai_errors(exc) from exc
    return AIModelResponse.model_validate(model)


@router.patch(
    "/models/{model_id}",
    response_model=AIModelResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def update_ai_model(
    model_id: UUID,
    payload: AIModelUpdateRequest,
    db: AsyncSession = Depends(get_db),
    service: AIModelService = Depends(get_ai_model_service),
) -> AIModelResponse:
    try:
        model = await service.set_model_enabled(db, model_id=model_id, enabled=payload.enabled)
    except Exception as exc:
        raise _handle_ai_errors(exc) from exc
    return AIModelResponse.model_validate(model)


@router.post("/infer", response_model=AIInferResponse, dependencies=[Depends(rate_limit("ai"))])
async def infer_ai_model(
    payload: AIInferRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: AIModelService = Depends(get_ai_model_service),
) -> AIInferResponse:
    try:
        result = await service.infer(
            db,
            actor=current_user,
            model_id=payload.model_id,
            task=payload.task,
            input_data=payload.input,
            metadata=payload.metadata,
        )
    except Exception as exc:
        raise _handle_ai_errors(exc) from exc

    usage = result.get("usage", {})
    return AIInferResponse(
        request_id=UUID(str(result["request_id"])),
        output=result["output"],
        model_type=result["model_type"],
        model_id=UUID(str(result["model_id"])),
        provider=result["provider"],
        model_name=result["model_name"],
        latency_ms=result["latency_ms"],
        usage=AIInferUsageResponse(**usage),
    )


@router.post(
    "/models/{model_id}/evaluations",
    response_model=AIEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def create_model_evaluation(
    model_id: UUID,
    payload: AIEvaluationCreateRequest,
    db: AsyncSession = Depends(get_db),
    service: AIModelService = Depends(get_ai_model_service),
) -> AIEvaluationResponse:
    try:
        record = await service.record_evaluation(
            db,
            model_id=model_id,
            evaluation_type=payload.evaluation_type,
            metrics=payload.metrics,
            dataset_ref=payload.dataset_ref,
            sample_count=payload.sample_count,
            notes=payload.notes,
        )
    except Exception as exc:
        raise _handle_ai_errors(exc) from exc
    return AIEvaluationResponse.model_validate(record)
