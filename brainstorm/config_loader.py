"""Declarative YAML config loading (AC-12 / AC-13)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .business.types import PersonaConfig, SessionConfig, StopConditionConfig
from .business.validation import validate_config


def parse_config(raw: dict[str, Any]) -> SessionConfig:
    """Parse a raw YAML mapping into a validated ``SessionConfig``."""
    personas = [
        PersonaConfig(
            persona_id=str(p.get("persona_id", "")),
            name=str(p.get("name", "")),
            role_description=str(p.get("role_description", "")),
        )
        for p in raw.get("personas", [])
    ]
    stop_raw = raw.get("stop_condition") or {}
    config = SessionConfig(
        topic=str(raw.get("topic", "")),
        personas=personas,
        scheduler=raw.get("scheduler", "round_robin"),
        stop_condition=StopConditionConfig(
            type=stop_raw.get("type", "manual"),
            max_speeches=stop_raw.get("max_speeches"),
        ),
    )
    validate_config(config)  # raises DomainError on AC-02/AC-03/AC-13
    return config


def load_config(path: str | Path) -> SessionConfig:
    """Load and validate a full session config from a YAML file."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return parse_config(raw)


def load_personas(path: str | Path) -> list[PersonaConfig]:
    """Load a persona roster from a YAML file (``personas:`` key or a bare list)."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    items = raw.get("personas", raw if isinstance(raw, list) else [])
    return [
        PersonaConfig(
            persona_id=str(p.get("persona_id", "")),
            name=str(p.get("name", "")),
            role_description=str(p.get("role_description", "")),
        )
        for p in items
    ]
