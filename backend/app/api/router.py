from fastapi import APIRouter

from app.api.v1 import (
    ai,
    analytics,
    audits,
    auth,
    chat,
    dashboard,
    health,
    it_requests,
    knowledge,
    observability,
    password_resets,
    tickets,
    users,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(tickets.router, tags=["tickets"])
api_router.include_router(knowledge.router, tags=["knowledge"])
api_router.include_router(ai.router, tags=["ai"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(it_requests.router, tags=["it-requests"])
api_router.include_router(password_resets.router, tags=["password-resets"])
api_router.include_router(observability.router)
api_router.include_router(analytics.router)
api_router.include_router(audits.router)
api_router.include_router(users.router, tags=["users"])
