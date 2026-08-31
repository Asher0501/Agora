"""Session lifecycle — create / resume (AC-01, ADR-0003)."""
from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from ..business.errors import NOT_FOUND, DomainError
from ..business.types import (
    PersonaConfig,
    Session,
    SessionConfig,
    StopConditionConfig,
)
from ..business.validation import validate_config


def generate_session_id() -> str:
    return str(uuid4())


def _config_to_dict(config: SessionConfig) -> dict[str, Any]:
    return {
        "topic": config.topic,
        "personas": [
            {
                "persona_id": p.persona_id,
                "name": p.name,
                "role_description": p.role_description,
            }
            for p in config.personas
        ],
        "scheduler": config.scheduler,
        "stop_condition": {
            "type": config.stop_condition.type,
            "max_speeches": config.stop_condition.max_speeches,
        },
    }


def _dict_to_config(raw: dict[str, Any]) -> SessionConfig:
    personas = [PersonaConfig(**p) for p in raw.get("personas", [])]
    stop = raw.get("stop_condition") or {}
    return SessionConfig(
        topic=raw.get("topic", ""),
        personas=personas,
        scheduler=raw.get("scheduler", "round_robin"),
        stop_condition=StopConditionConfig(
            type=stop.get("type", "manual"),
            max_speeches=stop.get("max_speeches"),
        ),
    )


async def create_session(repository: Any, config: SessionConfig) -> Session:
    """Validate, persist, and return a new running Session (AC-01)."""
    validate_config(config)  # raises DomainError on AC-02/AC-03/AC-13
    session_id = generate_session_id()
    now = time.time()
    cfg_dict = _config_to_dict(config)
    cfg_dict["created_at"] = now
    await repository.save_session_config(session_id, cfg_dict)
    await repository.update_session_status(
        session_id, {"status": "running", "current_seq": 0, "last_speaker_id": None}
    )
    return Session(
        session_id=session_id,
        topic=config.topic,
        personas=config.personas,
        scheduler=config.scheduler,
        stop_condition=config.stop_condition,
        status="running",
        current_seq=0,
        created_at=now,
    )


async def resume_session(repository: Any, session_id: str) -> Session:
    """Rebuild a Session from persisted state (ADR-0003)."""
    raw = await repository.load_session_config(session_id)
    if raw is None:
        raise DomainError(NOT_FOUND, f"会话 {session_id} 不存在")
    config = _dict_to_config(raw)
    status = await repository.load_session_status(session_id) or {}
    return Session(
        session_id=session_id,
        topic=config.topic,
        personas=config.personas,
        scheduler=config.scheduler,
        stop_condition=config.stop_condition,
        status=status.get("status", "running"),
        current_seq=status.get("current_seq", 0),
        created_at=float(raw.get("created_at", 0.0)),
    )
