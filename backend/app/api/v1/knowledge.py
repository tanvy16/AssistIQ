from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.rate_limit import rate_limit
from app.models.enums import KnowledgeDocumentStatus, UserRole
from app.models.user import User
from app.schemas.knowledge import (
    KnowledgeDocumentCreate,
    KnowledgeDocumentListResponse,
    KnowledgeDocumentResponse,
    KnowledgeDocumentUpdate,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
)
from app.services.knowledge_base_service import (
    KnowledgeAccessDeniedError,
    KnowledgeBaseService,
    KnowledgeError,
    KnowledgeNotFoundError,
    KnowledgeStateError,
    KnowledgeValidationError,
    get_knowledge_service,
)

router = APIRouter(prefix="/knowledge")


def _handle_knowledge_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, KnowledgeNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, KnowledgeAccessDeniedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, (KnowledgeValidationError, KnowledgeStateError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, KnowledgeError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error"
        )
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")


@router.get("", response_model=KnowledgeDocumentListResponse)
async def list_knowledge_documents(
    status_filter: KnowledgeDocumentStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: KnowledgeBaseService = Depends(get_knowledge_service),
) -> KnowledgeDocumentListResponse:
    documents = await service.list_documents(
        db, actor=current_user, status=status_filter
    )
    items = [KnowledgeDocumentResponse.model_validate(doc) for doc in documents]
    return KnowledgeDocumentListResponse(items=items, total=len(items))


@router.post(
    "",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def create_knowledge_document(
    payload: KnowledgeDocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: KnowledgeBaseService = Depends(get_knowledge_service),
) -> KnowledgeDocumentResponse:
    document = await service.create_document(
        db,
        actor=current_user,
        title=payload.title,
        description=payload.description,
        body=payload.body,
        category=payload.category,
        source=payload.source,
        metadata=payload.metadata,
    )
    return KnowledgeDocumentResponse.model_validate(document)


@router.get("/{document_id}", response_model=KnowledgeDocumentResponse)
async def get_knowledge_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: KnowledgeBaseService = Depends(get_knowledge_service),
) -> KnowledgeDocumentResponse:
    try:
        document = await service.get_document(db, actor=current_user, document_id=document_id)
    except KnowledgeError as exc:
        raise _handle_knowledge_errors(exc) from exc
    return KnowledgeDocumentResponse.model_validate(document)


@router.patch(
    "/{document_id}",
    response_model=KnowledgeDocumentResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def update_knowledge_document(
    document_id: UUID,
    payload: KnowledgeDocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: KnowledgeBaseService = Depends(get_knowledge_service),
) -> KnowledgeDocumentResponse:
    try:
        document = await service.update_document(
            db,
            actor=current_user,
            document_id=document_id,
            title=payload.title,
            description=payload.description,
            body=payload.body,
            category=payload.category,
            source=payload.source,
            metadata=payload.metadata,
        )
    except KnowledgeError as exc:
        raise _handle_knowledge_errors(exc) from exc
    return KnowledgeDocumentResponse.model_validate(document)


@router.post(
    "/{document_id}/publish",
    response_model=KnowledgeDocumentResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def publish_knowledge_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: KnowledgeBaseService = Depends(get_knowledge_service),
) -> KnowledgeDocumentResponse:
    try:
        document = await service.publish_document(
            db, actor=current_user, document_id=document_id
        )
    except KnowledgeError as exc:
        raise _handle_knowledge_errors(exc) from exc
    return KnowledgeDocumentResponse.model_validate(document)


@router.post(
    "/{document_id}/archive",
    response_model=KnowledgeDocumentResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def archive_knowledge_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: KnowledgeBaseService = Depends(get_knowledge_service),
) -> KnowledgeDocumentResponse:
    try:
        document = await service.archive_document(
            db, actor=current_user, document_id=document_id
        )
    except KnowledgeError as exc:
        raise _handle_knowledge_errors(exc) from exc
    return KnowledgeDocumentResponse.model_validate(document)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def delete_knowledge_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: KnowledgeBaseService = Depends(get_knowledge_service),
) -> None:
    try:
        await service.delete_document(db, actor=current_user, document_id=document_id)
    except KnowledgeError as exc:
        raise _handle_knowledge_errors(exc) from exc


@router.post("/search", response_model=KnowledgeSearchResponse, dependencies=[Depends(rate_limit("search"))])
async def search_knowledge(
    payload: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: KnowledgeBaseService = Depends(get_knowledge_service),
) -> KnowledgeSearchResponse:
    try:
        results = await service.search_published(
            db, query=payload.query, top_k=payload.top_k
        )
    except KnowledgeError as exc:
        raise _handle_knowledge_errors(exc) from exc

    items = [KnowledgeSearchResult.model_validate(item) for item in results]
    return KnowledgeSearchResponse(results=items, total=len(items))
