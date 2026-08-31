"""Configuration validation (AC-02 / AC-03 / AC-13)."""
from __future__ import annotations

from .errors import (
    INSUFFICIENT_PERSONAS,
    PERSONA_ROLE_REQUIRED,
    TOPIC_REQUIRED,
    DomainError,
)
from .types import SessionConfig


def validate_config(config: SessionConfig) -> None:
    """Raise the matching ``DomainError`` when a config invariant is violated.

    Check order matches contracts/public-api.md §3 ``create_session``: topic
    first, then the deduped persona count, then role descriptions.
    """
    if not config.topic or not config.topic.strip():
        raise DomainError(TOPIC_REQUIRED, "主题不能为空")

    persona_ids = {p.persona_id for p in config.personas if p.persona_id}
    if len(persona_ids) < 2:
        raise DomainError(INSUFFICIENT_PERSONAS, "一场头脑风暴至少需要两位参与者")

    for persona in config.personas:
        if not persona.role_description or not persona.role_description.strip():
            raise DomainError(
                PERSONA_ROLE_REQUIRED,
                f"人设 {persona.persona_id} 必须提供角色描述",
            )
