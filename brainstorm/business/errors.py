"""Domain error sentinels.

Envelope ``{code, message, details?}`` per contracts/public-api.md §5. The ``code``
is a neutral ``module.error_name`` snake-case token (module prefix ``session``); the
``message`` is human-facing text.
"""
from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """A domain sentinel error carrying a stable machine-readable ``code``."""

    def __init__(self, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            d["details"] = self.details
        return d


# Error codes — contracts/public-api.md §5.
# The first four are AC-derived; the last two are `# inferred` (sequence gap).
# Cross-session isolation is structural (namespace construction, spec AC-06/06b),
# not a runtime rejection — hence no cross_session_write/read sentinels.
TOPIC_REQUIRED = "session.topic_required"
INSUFFICIENT_PERSONAS = "session.insufficient_personas"
PERSONA_ROLE_REQUIRED = "session.persona_role_required"
ROUND_QUOTA_EXHAUSTED = "session.round_quota_exhausted"
NOT_FOUND = "session.not_found"
INVALID_STATE = "session.invalid_state"
