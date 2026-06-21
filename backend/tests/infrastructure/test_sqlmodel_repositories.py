"""SQLModel repository tests."""

from sqlmodel import Session

from app.domain.item.entities import Item
from app.domain.item.value_objects import ItemDescription, ItemTitle
from app.domain.user.entities import User
from app.domain.user.value_objects import EmailAddress, FullName, PasswordHash
from app.infrastructure.sqlmodel.item import ItemDTO, new_item_repository
from app.infrastructure.sqlmodel.user import UserDTO, new_user_repository


def test_user_dto_round_trip() -> None:
    user = User.create(
        EmailAddress("user@example.com"),
        PasswordHash("hash"),
        FullName("User"),
        is_superuser=True,
    )

    dto = UserDTO.from_entity(user)
    entity = dto.to_entity()

    assert dto.__tablename__ == "user"
    assert entity == user
    assert entity.email == user.email
    assert entity.is_superuser


def test_item_dto_round_trip(user: User) -> None:
    item = Item.create(
        user.id,
        ItemTitle("Item"),
        ItemDescription("Description"),
    )

    dto = ItemDTO.from_entity(item)
    entity = dto.to_entity()

    assert dto.__tablename__ == "item"
    assert entity == item
    assert entity.owner_id == user.id


def test_user_repository_persists_and_updates_users(db_session: Session) -> None:
    repository = new_user_repository(db_session)
    user = User.create(EmailAddress("user@example.com"), PasswordHash("hash"))

    repository.save(user)
    db_session.commit()

    found = repository.find_by_email(EmailAddress("user@example.com"))
    assert found == user
    assert repository.count() == 1

    user.update_full_name(FullName("Updated"))
    repository.save(user)
    db_session.commit()

    found = repository.find_by_id(user.id)
    assert found is not None
    assert found.full_name == FullName("Updated")

    repository.delete(user.id)
    db_session.commit()

    assert repository.find_by_id(user.id) is None


def test_item_repository_persists_filters_counts_and_deletes(
    db_session: Session,
) -> None:
    user_repository = new_user_repository(db_session)
    item_repository = new_item_repository(db_session)
    owner = User.create(EmailAddress("owner@example.com"), PasswordHash("hash"))
    other = User.create(EmailAddress("other@example.com"), PasswordHash("hash"))
    user_repository.save(owner)
    user_repository.save(other)

    item = Item.create(owner.id, ItemTitle("Owner item"), ItemDescription("Body"))
    other_item = Item.create(other.id, ItemTitle("Other item"))
    item_repository.save(item)
    item_repository.save(other_item)
    db_session.commit()

    assert item_repository.find_by_id(item.id) == item
    assert item_repository.count() == 2
    assert item_repository.count_by_owner_id(owner.id) == 1
    assert item_repository.find_by_owner_id(owner.id) == [item]

    item.update_content(ItemTitle("Updated"), None)
    item_repository.save(item)
    db_session.commit()

    found = item_repository.find_by_id(item.id)
    assert found is not None
    assert found.title == ItemTitle("Updated")

    item_repository.delete(item.id)
    db_session.commit()

    assert item_repository.find_by_id(item.id) is None
