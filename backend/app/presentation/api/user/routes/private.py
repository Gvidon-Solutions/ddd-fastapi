"""Private development-only routes."""

from fastapi import APIRouter

router = APIRouter(prefix="/private", tags=["private"])


@router.get("/health-check/")
async def private_health_check() -> bool:
    """Return private API health."""
    return True
