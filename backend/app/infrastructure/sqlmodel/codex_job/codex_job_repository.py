"""SQLModel implementation of the Codex job repository."""

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.codex_job.entities import CodexJob
from app.domain.codex_job.repositories import CodexJobRepository
from app.domain.codex_job.value_objects import CodexJobId
from app.infrastructure.sqlmodel.codex_job.codex_job_dto import CodexJobDTO


class CodexJobRepositoryImpl(CodexJobRepository):
    """Persist Codex jobs with SQLModel."""

    def __init__(self, session: AsyncSession):
        """Store the active SQLModel session."""
        self.session = session

    async def save(self, codex_job: CodexJob) -> None:
        """Insert or update a Codex job."""
        codex_job_dto = CodexJobDTO.from_entity(codex_job)
        existing_job = await self.session.get(CodexJobDTO, codex_job.id.value)
        if existing_job is None:
            self.session.add(codex_job_dto)
            return

        existing_job.prompt = codex_job_dto.prompt
        existing_job.status = codex_job_dto.status
        existing_job.backend_job_id = codex_job_dto.backend_job_id
        existing_job.result = codex_job_dto.result
        existing_job.error_message = codex_job_dto.error_message
        existing_job.created_at = codex_job_dto.created_at
        existing_job.started_at = codex_job_dto.started_at
        existing_job.finished_at = codex_job_dto.finished_at
        self.session.add(existing_job)

    async def find_by_id(self, codex_job_id: CodexJobId) -> CodexJob | None:
        """Return a Codex job by ID."""
        codex_job = await self.session.get(CodexJobDTO, codex_job_id.value)
        return codex_job.to_entity() if codex_job else None


def new_codex_job_repository(session: AsyncSession) -> CodexJobRepository:
    """Create a Codex job repository bound to the active session."""
    return CodexJobRepositoryImpl(session)
