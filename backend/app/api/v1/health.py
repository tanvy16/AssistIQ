from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core import config
from app.core.database import check_database_connection

router = APIRouter()


@router.get("/ready")
async def readiness_check():
    is_ready, diagnostic = await check_database_connection()
    if not is_ready:
        content = {
            "status": "not_ready",
            "database": "unavailable",
        }
        settings = config.get_settings()
        if settings.is_development and diagnostic is not None:
            content["reason"] = diagnostic["error_category"]
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=content,
        )

    return {
        "status": "ready",
        "database": "connected",
    }
