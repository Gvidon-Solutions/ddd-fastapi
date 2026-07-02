"""SQLModel implementation of the file repository."""

from __future__ import annotations

from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job import File, FileRepository
from app.infrastructure.sqlmodel.job.file_dto import FileDTO


class FileRepositoryImpl(FileRepository):
    """Persist file metadata with SQLModel."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, file: File) -> None:
        """Create file metadata."""
        self.session.add(FileDTO.from_entity(file))

    async def get(self, file_id: UUID) -> File:
        """Return file metadata."""
        file = await self.session.get(FileDTO, file_id)
        if file is None:
            raise KeyError(str(file_id))
        return file.to_entity()


def new_file_repository(session: AsyncSession) -> FileRepository:
    """Create a file repository bound to the active session."""
    return FileRepositoryImpl(session)
