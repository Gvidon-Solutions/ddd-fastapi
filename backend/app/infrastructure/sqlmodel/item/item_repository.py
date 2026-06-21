"""SQLModel implementation of the item repository."""

from sqlmodel import Session, col, func, select

from app.domain.item.entities import Item
from app.domain.item.repositories import ItemRepository
from app.domain.item.value_objects import ItemId
from app.domain.user.value_objects import UserId
from app.infrastructure.sqlmodel.item.item_dto import ItemDTO


class ItemRepositoryImpl(ItemRepository):
    """Persist item entities with SQLModel."""

    def __init__(self, session: Session):
        """Store the active SQLModel session."""
        self.session = session

    def save(self, item: Item) -> None:
        """Insert or update an item."""
        item_dto = ItemDTO.from_entity(item)
        existing_item = self.session.get(ItemDTO, item.id.value)
        if existing_item is None:
            self.session.add(item_dto)
            return

        existing_item.title = item_dto.title
        existing_item.description = item_dto.description
        existing_item.owner_id = item_dto.owner_id
        existing_item.created_at = item_dto.created_at
        self.session.add(existing_item)

    def find_by_id(self, item_id: ItemId) -> Item | None:
        """Return an item by ID."""
        item = self.session.get(ItemDTO, item_id.value)
        return item.to_entity() if item else None

    def find_all(self, offset: int = 0, limit: int = 100) -> list[Item]:
        """Return all items ordered newest first."""
        statement = (
            select(ItemDTO)
            .order_by(col(ItemDTO.created_at).desc())
            .offset(offset)
            .limit(limit)
        )
        return [item.to_entity() for item in self.session.exec(statement).all()]

    def find_by_owner_id(
        self,
        owner_id: UserId,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Item]:
        """Return items owned by one user."""
        statement = (
            select(ItemDTO)
            .where(ItemDTO.owner_id == owner_id.value)
            .order_by(col(ItemDTO.created_at).desc())
            .offset(offset)
            .limit(limit)
        )
        return [item.to_entity() for item in self.session.exec(statement).all()]

    def count(self) -> int:
        """Return the total item count."""
        statement = select(func.count()).select_from(ItemDTO)
        return self.session.exec(statement).one()

    def count_by_owner_id(self, owner_id: UserId) -> int:
        """Return the total item count for one user."""
        statement = (
            select(func.count())
            .select_from(ItemDTO)
            .where(ItemDTO.owner_id == owner_id.value)
        )
        return self.session.exec(statement).one()

    def delete(self, item_id: ItemId) -> None:
        """Delete an item by ID."""
        item = self.session.get(ItemDTO, item_id.value)
        if item is not None:
            self.session.delete(item)


def new_item_repository(session: Session) -> ItemRepository:
    """Create an item repository bound to the active session."""
    return ItemRepositoryImpl(session)
