from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.rate_limit import rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.runbooks.base import RunbookDisabledError, RunbookValidationError, UnknownRunbookError
from app.schemas.it_request import (
    AccessCatalogResponse,
    ApprovalActionRequest,
    CatalogEnableRequest,
    ITRequestCreate,
    ITRequestListItem,
    ITRequestListResponse,
    ITRequestResponse,
    RequestEventResponse,
    RunbookExecutionResponse,
    RunbookResponse,
    SoftwareCatalogResponse,
)
from app.services.it_request_service import (
    ITRequestAccessDeniedError,
    ITRequestNotFoundError,
    ITRequestService,
    ITRequestValidationError,
    get_it_request_service,
)

router = APIRouter(prefix="/it-requests")


def _handle(exc: Exception) -> HTTPException:
    if isinstance(exc, ITRequestNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ITRequestAccessDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(
        exc,
        (ITRequestValidationError, UnknownRunbookError, RunbookDisabledError, RunbookValidationError),
    ):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")


@router.post("", response_model=ITRequestResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit("it"))])
async def create_it_request(
    payload: ITRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ITRequestService = Depends(get_it_request_service),
) -> ITRequestResponse:
    try:
        request = await service.create_request(
            db,
            actor=current_user,
            message=payload.message,
            request_type=payload.request_type,
        )
    except Exception as exc:
        raise _handle(exc) from exc
    return ITRequestResponse.model_validate(request)


@router.get("", response_model=ITRequestListResponse)
async def list_it_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ITRequestService = Depends(get_it_request_service),
) -> ITRequestListResponse:
    items = await service.list_requests(db, actor=current_user)
    return ITRequestListResponse(
        items=[ITRequestListItem.model_validate(item) for item in items],
        total=len(items),
    )


@router.get("/catalog/software", response_model=list[SoftwareCatalogResponse])
async def list_software_catalog(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ITRequestService = Depends(get_it_request_service),
) -> list[SoftwareCatalogResponse]:
    items = await service.list_software_catalog(db)
    return [SoftwareCatalogResponse.model_validate(item) for item in items]


@router.get("/catalog/access", response_model=list[AccessCatalogResponse])
async def list_access_catalog(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ITRequestService = Depends(get_it_request_service),
) -> list[AccessCatalogResponse]:
    items = await service.list_access_catalog(db)
    return [AccessCatalogResponse.model_validate(item) for item in items]


@router.get("/runbooks", response_model=list[RunbookResponse])
async def list_runbooks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ITRequestService = Depends(get_it_request_service),
) -> list[RunbookResponse]:
    items = await service.list_runbooks(db)
    return [RunbookResponse.model_validate(item) for item in items]


@router.patch(
    "/catalog/software/{item_id}",
    response_model=SoftwareCatalogResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def update_software_catalog(
    item_id: UUID,
    payload: CatalogEnableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ITRequestService = Depends(get_it_request_service),
) -> SoftwareCatalogResponse:
    try:
        item = await service.set_catalog_enabled(
            db, actor=current_user, kind="software", item_id=item_id, enabled=payload.enabled
        )
    except Exception as exc:
        raise _handle(exc) from exc
    return SoftwareCatalogResponse.model_validate(item)


@router.patch(
    "/runbooks/{runbook_id}",
    response_model=RunbookResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def update_runbook(
    runbook_id: str,
    payload: CatalogEnableRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ITRequestService = Depends(get_it_request_service),
) -> RunbookResponse:
    try:
        item = await service.set_runbook_enabled(
            db, actor=current_user, runbook_id=runbook_id, enabled=payload.enabled
        )
    except Exception as exc:
        raise _handle(exc) from exc
    return RunbookResponse.model_validate(item)


@router.get("/{request_id}", response_model=ITRequestResponse)
async def get_it_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ITRequestService = Depends(get_it_request_service),
) -> ITRequestResponse:
    try:
        request = await service.get_request(db, actor=current_user, request_id=request_id)
    except Exception as exc:
        raise _handle(exc) from exc
    return ITRequestResponse.model_validate(request)


@router.get("/{request_id}/events", response_model=list[RequestEventResponse])
async def list_request_events(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ITRequestService = Depends(get_it_request_service),
) -> list[RequestEventResponse]:
    try:
        events = await service.list_events(db, actor=current_user, request_id=request_id)
    except Exception as exc:
        raise _handle(exc) from exc
    return [RequestEventResponse.model_validate(event) for event in events]


@router.get("/{request_id}/execution", response_model=RunbookExecutionResponse | None)
async def get_request_execution(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ITRequestService = Depends(get_it_request_service),
) -> RunbookExecutionResponse | None:
    try:
        execution = await service.get_execution(db, actor=current_user, request_id=request_id)
    except Exception as exc:
        raise _handle(exc) from exc
    if execution is None:
        return None
    return RunbookExecutionResponse.model_validate(execution)


@router.post("/{request_id}/approve", response_model=ITRequestResponse)
async def approve_request(
    request_id: UUID,
    payload: ApprovalActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ITRequestService = Depends(get_it_request_service),
) -> ITRequestResponse:
    try:
        request = await service.approve(
            db, actor=current_user, request_id=request_id, comment=payload.comment
        )
    except Exception as exc:
        raise _handle(exc) from exc
    return ITRequestResponse.model_validate(request)


@router.post("/{request_id}/reject", response_model=ITRequestResponse)
async def reject_request(
    request_id: UUID,
    payload: ApprovalActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ITRequestService = Depends(get_it_request_service),
) -> ITRequestResponse:
    try:
        request = await service.reject(
            db, actor=current_user, request_id=request_id, comment=payload.comment
        )
    except Exception as exc:
        raise _handle(exc) from exc
    return ITRequestResponse.model_validate(request)


@router.post("/{request_id}/cancel", response_model=ITRequestResponse)
async def cancel_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: ITRequestService = Depends(get_it_request_service),
) -> ITRequestResponse:
    try:
        request = await service.cancel(db, actor=current_user, request_id=request_id)
    except Exception as exc:
        raise _handle(exc) from exc
    return ITRequestResponse.model_validate(request)
