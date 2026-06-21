"""API router aggregation."""

from fastapi import APIRouter

from app.config import settings
from app.presentation.api.agent.routes import codex, events
from app.presentation.api.item.routes import items
from app.presentation.api.user.routes import login, private, users
from app.presentation.api.utils.routes import utils

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(codex.router)
api_router.include_router(events.router)

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
