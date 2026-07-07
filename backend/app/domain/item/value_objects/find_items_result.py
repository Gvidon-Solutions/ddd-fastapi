"""Define item listing result value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.item.entities import Item


@dataclass(frozen=True)
class FindItemsResult:
    """Represent a paginated item listing result."""

    data: list[Item]
    count: int
