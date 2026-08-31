"""Pure domain layer — types, error sentinels, extension protocols. Zero weave dependency."""

from .errors import (
    CROSS_SESSION_READ,
    CROSS_SESSION_WRITE,
    INSUFFICIENT_PERSONAS,
    INVALID_STATE,
    NOT_FOUND,
    PERSONA_ROLE_REQUIRED,
    ROUND_QUOTA_EXHAUSTED,
    TOPIC_REQUIRED,
    DomainError,
)
from .namespaces import (
    STATE_KEY_CONCLUSION,
    STATE_KEY_CONFIG,
    STATE_KEY_STATUS,
    persona_state_ns,
    persona_stream_ns,
    session_events_ns,
    session_state_ns,
    session_stream_ns,
)
from .protocols import (
    Consumer,
    Continue,
    PrivateMemory,
    ProgressEvent,
    Role,
    RoleContext,
    Scheduler,
    SchedulerContext,
    SchedulingDecision,
    Stop,
    StopCondition,
    StopConditionContext,
    StopDecision,
)
from .types import (
    PersonaConfig,
    SchedulerKind,
    Session,
    SessionConfig,
    SessionOutcome,
    SessionStatus,
    Speech,
    StopConditionConfig,
    StopConditionKind,
)
from .validation import validate_config

__all__ = [
    # errors
    "DomainError",
    "TOPIC_REQUIRED",
    "INSUFFICIENT_PERSONAS",
    "PERSONA_ROLE_REQUIRED",
    "ROUND_QUOTA_EXHAUSTED",
    "CROSS_SESSION_WRITE",
    "CROSS_SESSION_READ",
    "NOT_FOUND",
    "INVALID_STATE",
    # namespaces
    "STATE_KEY_CONFIG",
    "STATE_KEY_STATUS",
    "STATE_KEY_CONCLUSION",
    "session_stream_ns",
    "session_state_ns",
    "session_events_ns",
    "persona_stream_ns",
    "persona_state_ns",
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
    # types
    "PersonaConfig",
    "SessionConfig",
    "StopConditionConfig",
    "Session",
    "Speech",
    "SessionOutcome",
    "SchedulerKind",
    "StopConditionKind",
    "SessionStatus",
    # validation
    "validate_config",
]
