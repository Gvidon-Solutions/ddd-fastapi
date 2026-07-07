"""Provide the use case for deleting the current user."""

from abc import ABC, abstractmethod

from app.domain.job import JobRepository
from app.domain.user.entities import User
from app.domain.user.repositories import UserRepository


class DeleteCurrentUserUseCase(ABC):
    """Define the application boundary for current-user deletion."""

    @abstractmethod
    async def execute(self, current_user: User) -> None:
        """Delete the current user."""


class DeleteCurrentUserUseCaseImpl(DeleteCurrentUserUseCase):
    """Delete the current user through repository abstractions."""

    def __init__(
        self,
        user_repository: UserRepository,
        job_repository: JobRepository | None = None,
    ):
        """Store use case dependencies."""
        self.user_repository = user_repository
        self.job_repository = job_repository

    async def execute(self, current_user: User) -> None:
        """Delete the current user when domain rules allow it."""
        current_user.ensure_can_delete_self()
        if self.job_repository is not None:
            summaries = await self.job_repository.list_by_initiator(str(current_user.id))
            for summary in summaries:
                await self.job_repository.delete(summary.id, cascade_children=True)
        await self.user_repository.delete(current_user.id)


def new_delete_current_user_use_case(
    user_repository: UserRepository,
    job_repository: JobRepository | None = None,
) -> DeleteCurrentUserUseCase:
    """Instantiate the current-user delete use case."""
    return DeleteCurrentUserUseCaseImpl(
        user_repository,
        job_repository=job_repository,
    )
