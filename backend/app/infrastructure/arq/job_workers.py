"""ARQ worker bindings for job contracts."""

from __future__ import annotations

from collections.abc import Callable

from app.domain.job import JobContract, job_registry


class JobWorkerBindingRegistry:
    """Map job contracts to ARQ worker functions."""

    def __init__(self) -> None:
        self._bindings: dict[tuple[str, str], Callable] = {}

    def register(self, contract: type[JobContract], function: Callable) -> Callable:
        """Register a worker function for a contract."""
        job_registry.get(type=contract.type, version=contract.version)
        self._bindings[(contract.type, contract.version)] = function
        return function

    def get(self, *, type: str, version: str) -> Callable | None:
        """Return a worker function for a contract, if one is bound."""
        return self._bindings.get((type, version))

    def functions(self) -> list[Callable]:
        """Return registered ARQ worker functions."""
        return list(dict.fromkeys(self._bindings.values()))


worker_bindings = JobWorkerBindingRegistry()


def job_worker(contract: type[JobContract]):
    """Decorate an ARQ worker function with an executable job contract."""

    def decorator(function: Callable) -> Callable:
        return worker_bindings.register(contract, function)

    return decorator
