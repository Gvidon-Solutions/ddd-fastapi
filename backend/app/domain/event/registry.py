"""Build a registry for typed domain events."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from functools import lru_cache
from typing import Literal, get_args, get_origin, get_type_hints

import app.domain
from app.domain.event.entities import Event


@lru_cache(maxsize=1)
def get_event_type_registry() -> dict[str, type[Event]]:
    """Return event type identifiers mapped to concrete event classes."""
    registry: dict[str, type[Event]] = {}
    for module_info in pkgutil.walk_packages(
        app.domain.__path__,
        prefix=f"{app.domain.__name__}.",
    ):
        module = importlib.import_module(module_info.name)
        for _, event_class in inspect.getmembers(module, _is_concrete_event_class):
            event_type = _event_type_literal(event_class)
            if event_type is None:
                continue
            existing_event_class = registry.get(event_type)
            if existing_event_class is not None and existing_event_class is not event_class:
                raise ValueError(f"Duplicate event type: {event_type}")
            registry[event_type] = event_class
    return registry


def get_event_class(event_type: str) -> type[Event] | None:
    """Return the concrete event class for an event type identifier."""
    return get_event_type_registry().get(event_type)


def _is_concrete_event_class(candidate) -> bool:
    return (
        inspect.isclass(candidate)
        and issubclass(candidate, Event)
        and candidate is not Event
    )


def _event_type_literal(event_class: type[Event]) -> str | None:
    event_type_hint = get_type_hints(event_class).get("type")
    if get_origin(event_type_hint) is not Literal:
        return None
    event_type_args = get_args(event_type_hint)
    if len(event_type_args) != 1 or not isinstance(event_type_args[0], str):
        raise TypeError(f"Event type must be a single string Literal: {event_class}")
    return event_type_args[0]
