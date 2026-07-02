"""Registry for versioned job contracts."""

from __future__ import annotations

from app.domain.job.base.exceptions import (
    DuplicateJobContractError,
    UnknownJobContractError,
)
from app.domain.job.base.job_contract import JobContract


class JobRegistry:
    """Map ``(type, version)`` pairs to contract classes."""

    def __init__(self) -> None:
        self._contracts: dict[tuple[str, str], type[JobContract]] = {}

    def register(self, contract: type[JobContract]) -> type[JobContract]:
        """Register a contract class and reject duplicates."""
        key = (contract.type, contract.version)
        existing = self._contracts.get(key)
        if existing is not None and existing is not contract:
            raise DuplicateJobContractError(
                f"Job contract already registered: {contract.type} {contract.version}"
            )
        self._contracts[key] = contract
        return contract

    def get(self, *, type: str, version: str) -> type[JobContract]:
        """Return a registered contract class."""
        try:
            return self._contracts[(type, version)]
        except KeyError as exc:
            raise UnknownJobContractError(f"Unknown job contract: {type} {version}") from exc

    def contains(self, *, type: str, version: str) -> bool:
        """Return whether a contract is registered."""
        return (type, version) in self._contracts

    def all(self) -> tuple[type[JobContract], ...]:
        """Return all registered contracts."""
        return tuple(self._contracts.values())


job_registry = JobRegistry()
