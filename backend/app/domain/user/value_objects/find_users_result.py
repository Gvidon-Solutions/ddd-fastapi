"""Define user listing result value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.user.entities import User


@dataclass(frozen=True)
class FindUsersResult:
    """Represent a paginated user listing result."""

    data: list[User]
    count: int
