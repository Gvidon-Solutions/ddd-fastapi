"""Event registry tests."""

from app.domain.event import get_event_class, get_event_type_registry
from app.domain.job.codex_auth_job_use_case import (
    Event1CodexAuthStarted,
    Event2UserLoginRequested,
    Event3CodexAuthSucceeded,
    Event4CodexAuthFailed,
)


def test_event_registry_discovers_domain_event_classes_by_literal_type() -> None:
    # Act
    registry = get_event_type_registry()

    # Assert
    assert registry["CodexAuthStartedV1"] is Event1CodexAuthStarted
    assert registry["CodexAuthUserLoginRequestedV1"] is Event2UserLoginRequested
    assert registry["CodexAuthSucceededV1"] is Event3CodexAuthSucceeded
    assert registry["CodexAuthFailedV1"] is Event4CodexAuthFailed
    assert get_event_class("CodexAuthSucceededV1") is Event3CodexAuthSucceeded
