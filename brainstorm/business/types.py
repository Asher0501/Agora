"""Domain types — the typed mapping of data-model.md entities (zero weave)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SchedulerKind = Literal["round_robin", "moderator"]
StopConditionKind = Literal["fixed_rounds", "convergence", "manual"]
SessionStatus = Literal["running", "stopped"]


@dataclass(frozen=True)
class PersonaConfig:
    """A persona on the roster (data-model PERSONA_INSTANCE)."""

    persona_id: str
    name: str = ""
    role_description: str = ""


@dataclass(frozen=True)
class StopConditionConfig:
    """The session's stop condition (data-model SESSION.config.stop_condition)."""

    type: StopConditionKind
    max_speeches: int | None = None


@dataclass(frozen=True)
class SessionConfig:
    """Declarative session configuration (data-model SESSION.config)."""

    topic: str
    personas: list[PersonaConfig]
    scheduler: SchedulerKind = "round_robin"
    stop_condition: StopConditionConfig = field(
        default_factory=lambda: StopConditionConfig(type="manual")
    )


@dataclass(frozen=True)
class Session:
    """A brainstorm session aggregate root (data-model SESSION)."""

    session_id: str
    topic: str
    personas: list[PersonaConfig]
    scheduler: SchedulerKind
    stop_condition: StopConditionConfig
    status: SessionStatus = "running"
    current_seq: int = 0
    created_at: float = 0.0


@dataclass(frozen=True)
class Speech:
    """One speech on the shared table (data-model SPEECH)."""

    seq: int
    speaker_id: str
    text: str
    created_at: float = 0.0


@dataclass(frozen=True)
class SessionOutcome:
    """What a finished session yields (data-model SESSION.conclusion + full record)."""

    session_id: str
    status: SessionStatus
    converged: bool
    conclusion: str | None
    speeches: list[Speech]
