"""Utility API routes."""

from fastapi import APIRouter, Depends
from pydantic.networks import EmailStr

from app.infrastructure.email import generate_test_email, send_email
from app.presentation.api.common import Message
from app.presentation.api.common.deps import get_current_active_superuser

router = APIRouter(prefix="/utils", tags=["utils"])


@router.post(
    "/test-email/",
    dependencies=[Depends(get_current_active_superuser)],
    status_code=201,
)
def test_email(email_to: EmailStr) -> Message:
    """Send a test email."""
    email_data = generate_test_email(email_to=email_to)
    send_email(
        email_to=email_to,
        subject=email_data.subject,
        html_content=email_data.html_content,
    )
    return Message(message="Test email sent")


@router.get("/health-check/")
async def health_check() -> bool:
    """Return API health."""
    return True
