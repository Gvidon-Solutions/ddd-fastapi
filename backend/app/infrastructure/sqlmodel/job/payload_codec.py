"""Pydantic-backed codec for persisted job payloads."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from functools import lru_cache
from typing import Any, cast

from pydantic import ConfigDict, TypeAdapter, ValidationError
from pydantic.dataclasses import dataclass as pydantic_dataclass

from app.domain.job.base.exceptions import JobSerializationError


def load_payload[T](value: object, target_type: type[T]) -> T:
    """Validate JSON-compatible data and return the original dataclass type."""
    try:
        decoded = _type_adapter(target_type).validate_python(value)
        return _restore_dataclass_type(decoded, target_type)
    except JobSerializationError:
        raise
    except ValidationError as exc:
        raise JobSerializationError(str(exc)) from exc
    except Exception as exc:
        raise JobSerializationError(str(exc)) from exc


def dump_payload(value: object) -> object:
    """Serialize a dataclass payload to JSON-compatible data."""
    try:
        return _type_adapter(type(value)).dump_python(value, mode="json")
    except JobSerializationError:
        raise
    except ValidationError as exc:
        raise JobSerializationError(str(exc)) from exc
    except Exception as exc:
        raise JobSerializationError(str(exc)) from exc


@lru_cache
def _type_adapter(target_type: type) -> TypeAdapter:
    return TypeAdapter(_pydantic_dataclass_type(target_type))


@lru_cache
def _pydantic_dataclass_type(target_type: type) -> type:
    if not is_dataclass(target_type):
        return target_type

    params = cast(Any, target_type).__dataclass_params__
    return cast(
        type,
        pydantic_dataclass(
            target_type,
            frozen=bool(getattr(params, "frozen", False)),
            config=ConfigDict(extra="forbid", revalidate_instances="always"),
        ),
    )


def _restore_dataclass_type[T](value: Any, target_type: type[T]) -> T:
    if not is_dataclass(target_type):
        return value
    if type(value) is target_type:
        return value
    if not isinstance(value, target_type):
        raise JobSerializationError(
            f"Expected {target_type.__name__}, got {type(value).__name__}"
        )
    return target_type(
        **{field.name: getattr(value, field.name) for field in fields(target_type)}
    )
