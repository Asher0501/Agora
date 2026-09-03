"""brainstorm — multi-persona brainstorm engine (library-sdk + cli).

Stable kernel (session lifecycle, turn loop, shared table, extension registry)
with four pluggable extension points (role / scheduler / stop-condition / consumer).

Layering (see docs/features/brainstorm/sad.md §5):
    business/       — pure domain types, zero weave dependency
    engine/         — kernel orchestration
    extensions/     — default pluggable implementations
    weave_adapter/  — the single weave integration point (persistence + LLM)
    cli/            — command-line driver

Public Python API (contracts/public-api.md §3):
    create_session / run_session / stop_session / resume_session / read_table
    + the four extension-point protocols and the Registry for registering them.
"""

from .business import (
    INSUFFICIENT_PERSONAS,
    INVALID_STATE,
    NOT_FOUND,
    PERSONA_ROLE_REQUIRED,
    ROUND_QUOTA_EXHAUSTED,
    TOPIC_REQUIRED,
    Consumer,
    Continue,
    DomainError,
    PersonaConfig,
    PrivateMemory,
    ProgressEvent,
    Role,
    RoleContext,
    Scheduler,
    SchedulerContext,
    SchedulingDecision,
    Session,
    SessionConfig,
    SessionOutcome,
    SessionStatus,
    Speech,
    Stop,
    StopCondition,
    StopConditionConfig,
    StopConditionContext,
    StopConditionKind,
    StopDecision,
    validate_config,
)
from .engine.loop import run_session
from .engine.registry import Registry
from .engine.session import create_session, resume_session
from .engine.stop import stop_session
from .engine.table import read_table
from .weave_adapter.repository import Repository

__version__ = "0.1.0"

__all__ = [
    # operations
    "create_session",
    "resume_session",
    "run_session",
    "stop_session",
    "read_table",
    "Repository",
    "Registry",
    # errors
    "DomainError",
    "TOPIC_REQUIRED",
    "INSUFFICIENT_PERSONAS",
    "PERSONA_ROLE_REQUIRED",
    "ROUND_QUOTA_EXHAUSTED",
    "NOT_FOUND",
    "INVALID_STATE",
    # types
    "PersonaConfig",
    "SessionConfig",
    "StopConditionConfig",
    "Session",
    "Speech",
    "SessionOutcome",
    "SessionStatus",
    "StopConditionKind",
    # protocols
    "Role",
    "RoleContext",
    "Scheduler",
    "SchedulerContext",
    "SchedulingDecision",
    "StopCondition",
    "StopConditionContext",
    "StopDecision",
    "Stop",
    "Continue",
    "Consumer",
    "ProgressEvent",
    "PrivateMemory",
    # validation
    "validate_config",
]
