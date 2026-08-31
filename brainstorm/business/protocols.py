"""Extension-point protocols and their context types (public-api.md §4)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .types import PersonaConfig, Speech


@dataclass(frozen=True)
class ProgressEvent:
    """An observability event published on the in-process bus (ADR-0004)."""

    name: str
    session_id: str
    payload: dict[str, Any] = field(default_factory=dict)


class PrivateMemory(Protocol):
    """A persona-private memory handle (ADR-0006). Others cannot read it."""

    async def read(self, key: str) -> Any | None:
        """Read a private state key."""

    async def write(self, key: str, value: Any) -> None:
        """Write (upsert) a private state key."""


@dataclass(frozen=True)
class RoleContext:
    """Context handed to a Role when it is its turn to speak."""

    topic: str
    history: list[Speech]  # windowed (sad §8)
    private_memory: PrivateMemory


class Role(Protocol):
    """A persona that produces a speech (ADR-0002 extension point)."""

    async def speak(self, ctx: RoleContext) -> str: ...


@dataclass(frozen=True)
class SchedulerContext:
    """Context handed to a Scheduler to pick the next speaker."""

    session_id: str
    topic: str
    personas: list[PersonaConfig]
    last_speaker_id: str | None
    current_seq: int
    history: list[Speech]


class Scheduler(Protocol):
    """Picks the next speaker's persona_id (ADR-0002 extension point)."""

    def next_speaker(self, ctx: SchedulerContext) -> str: ...


@dataclass(frozen=True)
class StopDecision:
    """A stop-condition evaluation result (Stop | Continue)."""

    stop: bool
    conclusion: str | None = None
    converged: bool = False


# Module-level singletons; a convergence stop may instead return a
# StopDecision(stop=True, conclusion=...) to carry the router's conclusion.
Continue = StopDecision(stop=False)
Stop = StopDecision(stop=True)


@dataclass(frozen=True)
class StopConditionContext:
    """Context handed to a StopCondition after each speech lands."""

    session_id: str
    current_seq: int
    max_speeches: int | None
    converged: bool = False
    conclusion: str | None = None
    stop_requested: bool = False


class StopCondition(Protocol):
    """Decides whether the session should end (ADR-0002 extension point)."""

    def evaluate(self, ctx: StopConditionContext) -> StopDecision: ...


class Consumer(Protocol):
    """Subscribes to observability progress events (ADR-0002 extension point)."""

    def on_event(self, event: ProgressEvent) -> None: ...
