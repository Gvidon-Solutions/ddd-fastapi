"""Strict dataclass JSON codec for job contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import MISSING, fields, is_dataclass
from datetime import datetime
from enum import Enum
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints
from uuid import UUID

from app.domain.job.base.exceptions import JobSerializationError


def serialize_json(value: object) -> object:
    """Convert a typed object into JSON-compatible data."""
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: serialize_json(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [serialize_json(item) for item in value]
    if isinstance(value, tuple):
        return [serialize_json(item) for item in value]
    if isinstance(value, dict):
        return {
            _serialize_dict_key(key): serialize_json(item)
            for key, item in value.items()
        }
    raise JobSerializationError(f"Unsupported JSON value: {value!r}")


def deserialize_json(value: object, target_type: type):
    """Decode JSON-compatible data into ``target_type`` with runtime checks."""
    try:
        return _decode(value, target_type)
    except JobSerializationError:
        raise
    except Exception as exc:
        raise JobSerializationError(str(exc)) from exc


def _decode(value: object, target_type: Any):
    origin = get_origin(target_type)
    args = get_args(target_type)

    if origin is UnionType or origin is Union:
        return _decode_union(value, args)
    if target_type is Any or target_type is object:
        return value
    if target_type is None or target_type is type(None):
        if value is not None:
            raise JobSerializationError(f"Expected null, got {type(value).__name__}")
        return None
    if is_dataclass(target_type):
        return _decode_dataclass(value, target_type)
    if isinstance(target_type, type) and issubclass(target_type, Enum):
        return _decode_enum(value, target_type)
    if target_type is UUID:
        if not isinstance(value, str):
            raise JobSerializationError("Expected UUID string")
        return UUID(value)
    if target_type is datetime:
        if not isinstance(value, str):
            raise JobSerializationError("Expected datetime string")
        return datetime.fromisoformat(value)
    if origin is list:
        if not isinstance(value, list):
            raise JobSerializationError("Expected list")
        item_type = args[0] if args else object
        return [_decode(item, item_type) for item in value]
    if origin is tuple:
        if not isinstance(value, list | tuple):
            raise JobSerializationError("Expected tuple/list")
        return _decode_tuple(value, args)
    if origin is dict:
        if not isinstance(value, Mapping):
            raise JobSerializationError("Expected dict")
        key_type = args[0] if args else str
        value_type = args[1] if len(args) > 1 else object
        return {
            _decode_dict_key(key, key_type): _decode(item, value_type)
            for key, item in value.items()
        }
    if target_type in (str, int, float, bool):
        if type(value) is not target_type:
            raise JobSerializationError(
                f"Expected {target_type.__name__}, got {type(value).__name__}"
            )
        return value
    if isinstance(target_type, type):
        if not isinstance(value, target_type):
            raise JobSerializationError(
                f"Expected {target_type.__name__}, got {type(value).__name__}"
            )
        return value
    raise JobSerializationError(f"Unsupported type hint: {target_type!r}")


def _decode_union(value: object, args: tuple[Any, ...]):
    errors: list[str] = []
    for arg in args:
        try:
            return _decode(value, arg)
        except JobSerializationError as exc:
            errors.append(str(exc))
    raise JobSerializationError("; ".join(errors))


def _decode_dataclass(value: object, target_type: type):
    if not isinstance(value, Mapping):
        raise JobSerializationError(f"Expected object for {target_type.__name__}")
    field_names = {field.name for field in fields(target_type)}
    unknown = set(value) - field_names
    if unknown:
        raise JobSerializationError(
            f"Unknown fields for {target_type.__name__}: {sorted(unknown)}"
        )

    hints = get_type_hints(target_type)
    kwargs = {}
    for field in fields(target_type):
        if field.name in value:
            kwargs[field.name] = _decode(
                value[field.name],
                hints.get(field.name, field.type),
            )
            continue
        if field.default is not MISSING or field.default_factory is not MISSING:
            continue
        raise JobSerializationError(
            f"Missing required field for {target_type.__name__}: {field.name}"
        )
    return target_type(**kwargs)


def _decode_enum(value: object, target_type: type[Enum]):
    try:
        return target_type(value)
    except ValueError as exc:
        raise JobSerializationError(
            f"Invalid {target_type.__name__}: {value!r}"
        ) from exc


def _decode_tuple(value: object, args: tuple[Any, ...]) -> tuple:
    items = list(value)
    if len(args) == 2 and args[1] is Ellipsis:
        return tuple(_decode(item, args[0]) for item in items)
    if args and len(items) != len(args):
        raise JobSerializationError("Tuple length mismatch")
    return tuple(_decode(item, arg) for item, arg in zip(items, args, strict=True))


def _serialize_dict_key(key: object) -> str:
    if isinstance(key, str):
        return key
    if isinstance(key, Enum):
        return str(key.value)
    if isinstance(key, UUID):
        return str(key)
    if isinstance(key, int | float | bool):
        return str(key)
    raise JobSerializationError(f"Unsupported dict key: {key!r}")


def _decode_dict_key(key: object, target_type: Any):
    if target_type is str or target_type is object or target_type is Any:
        if not isinstance(key, str):
            raise JobSerializationError("Expected string dict key")
        return key
    if target_type is int:
        return int(key)
    if target_type is UUID:
        if not isinstance(key, str):
            raise JobSerializationError("Expected UUID dict key string")
        return UUID(key)
    if isinstance(target_type, type) and issubclass(target_type, Enum):
        return target_type(key)
    raise JobSerializationError(f"Unsupported dict key type: {target_type!r}")
