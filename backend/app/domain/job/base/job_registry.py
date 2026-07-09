"""Build a registry for typed job entities."""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from functools import lru_cache
from typing import Literal, get_args, get_origin, get_type_hints

import app.domain
from app.domain.job.base.entities import Job
from app.domain.job.base.exceptions import DuplicateJobContractError

type JobTypeRegistry = dict[tuple[str, str], type[Job]]


@lru_cache(maxsize=1)
def get_job_type_registry() -> JobTypeRegistry:
    """Return job type/version identifiers mapped to concrete job entities."""
    registry: JobTypeRegistry = {}
    for module_info in pkgutil.walk_packages(
        app.domain.__path__,
        prefix=f"{app.domain.__name__}.",
    ):
        module = importlib.import_module(module_info.name)
        for _, job_class in inspect.getmembers(module, _is_concrete_job_class):
            job_type = _job_literal(job_class, "type")
            job_version = _job_literal(job_class, "version")
            if job_type is None or job_version is None:
                continue
            key = (job_type, job_version)
            existing_job_class = registry.get(key)
            if existing_job_class is not None and existing_job_class is not job_class:
                raise DuplicateJobContractError(
                    f"Duplicate job type/version: {job_type} {job_version}"
                )
            registry[key] = job_class
    return registry


def get_job_class(*, type: str, version: str) -> type[Job] | None:
    """Return the concrete job entity for a type/version identifier."""
    return get_job_type_registry().get((type, version))


def _is_concrete_job_class(candidate) -> bool:
    return (
        inspect.isclass(candidate)
        and issubclass(candidate, Job)
        and candidate is not Job
        and _has_payload_classes(candidate)
    )


def _job_literal(job_class: type[Job], field_name: str) -> str | None:
    field_hint = get_type_hints(job_class).get(field_name)
    if get_origin(field_hint) is not Literal:
        return None
    field_args = get_args(field_hint)
    if len(field_args) != 1 or not isinstance(field_args[0], str):
        raise TypeError(
            f"Job {field_name} must be a single string Literal: {job_class}"
    )
    return field_args[0]


def _has_payload_classes(job_class: type[Job]) -> bool:
    input_type = getattr(job_class, "input", None)
    result_type = getattr(job_class, "result", None)
    return isinstance(input_type, type) and isinstance(result_type, type)
