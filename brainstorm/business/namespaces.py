"""Namespace and state-key builders (sad §8 / data-model.md).

Weave resolves the *last* ``:``-delimited segment of a namespace as the access
type (``stream`` / ``state`` / ``knowledge``). Every builder below therefore ends
in a legal access type. System events are stream rows in a namespace distinct
from the shared table so they stay off ``read_table``'s path — data-model.md's
literal ``:events`` suffix would violate weave's ``{scope}:{id}:{access}``
convention, so we render it as ``:events:stream``.
"""
from __future__ import annotations

# State keys under the session-state namespace (data-model §SESSION).
STATE_KEY_CONFIG = "config"
STATE_KEY_STATUS = "status"
STATE_KEY_CONCLUSION = "conclusion"


def session_stream_ns(session_id: str) -> str:
    """Shared table namespace (append-only speeches)."""
    return f"brainstorm:{session_id}:stream"


def session_state_ns(session_id: str) -> str:
    """Session state namespace (config / status / conclusion)."""
    return f"brainstorm:{session_id}:state"


def session_events_ns(session_id: str) -> str:
    """System-event namespace (skip / invalid_choice), kept off the table."""
    return f"brainstorm:{session_id}:events:stream"


def persona_stream_ns(session_id: str, persona_id: str) -> str:
    """A persona's private append-only notes (ADR-0006)."""
    return f"persona:{session_id}:{persona_id}:stream"


def persona_state_ns(session_id: str, persona_id: str) -> str:
    """A persona's private keyed state (ADR-0006)."""
    return f"persona:{session_id}:{persona_id}:state"
