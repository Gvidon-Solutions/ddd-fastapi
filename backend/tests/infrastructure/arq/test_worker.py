"""ARQ configuration tests."""

from app.infrastructure.arq import (
    ArqCodexJobStarter,
    WorkerSettings,
    new_codex_job_starter,
    run_codex_job,
)


def test_arq_infrastructure_is_importable() -> None:
    # Act & Assert
    assert ArqCodexJobStarter is not None
    assert WorkerSettings is not None
    assert new_codex_job_starter is not None
    assert run_codex_job is not None
    assert WorkerSettings.allow_abort_jobs is True
