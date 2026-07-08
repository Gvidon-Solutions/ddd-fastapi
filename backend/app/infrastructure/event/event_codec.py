"""Infrastructure codec for domain events."""

from __future__ import annotations

from typing import cast

import msgspec

from app.domain.event import Event

_encoder = msgspec.json.Encoder()
_decoder = msgspec.json.Decoder()


def dump_event(event: Event) -> dict[str, object]:
    """Serialize a domain event to an infrastructure event record."""
    record = _to_dict(event)
    record["type"] = event.type
    record["version"] = event.version
    return record


def dump_event_payload(payload: object) -> dict:
    """Serialize an event payload to an infrastructure payload record."""
    return _to_dict(payload)


def load_event_payload[T](value: object, target_type: type[T]) -> T:
    """Load an infrastructure payload record as a typed domain payload."""
    try:
        return msgspec.convert(value, type=target_type, strict=False)
    except (msgspec.ValidationError, TypeError, ValueError) as exc:
        raise ValueError(str(exc)) from exc


def _to_dict(value: object) -> dict[str, object]:
    record = _decoder.decode(_encoder.encode(value))
    if not isinstance(record, dict):
        raise ValueError("Event value must serialize to a dictionary")
    return cast(dict[str, object], record)
