"""Extension registry — the kernel's pluggable-extension lookup (ADR-0002)."""
from __future__ import annotations

from typing import Any


class Registry:
    """Name-keyed store for roles, schedulers, stop conditions, and consumers."""

    def __init__(self) -> None:
        self._roles: dict[str, Any] = {}
        self._schedulers: dict[str, Any] = {}
        self._stop_conditions: dict[str, Any] = {}
        self._consumers: list[Any] = []

    def register_role(self, name: str, role: Any) -> None:
        self._roles[name] = role

    def register_scheduler(self, name: str, scheduler: Any) -> None:
        self._schedulers[name] = scheduler

    def register_stop_condition(self, name: str, condition: Any) -> None:
        self._stop_conditions[name] = condition

    def register_consumer(self, consumer: Any) -> None:
        self._consumers.append(consumer)

    def get_role(self, name: str) -> Any:
        return self._roles[name]

    def get_scheduler(self, name: str) -> Any:
        return self._schedulers[name]

    def get_stop_condition(self, name: str) -> Any:
        return self._stop_conditions[name]

    @property
    def consumers(self) -> list[Any]:
        return list(self._consumers)
