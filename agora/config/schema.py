"""声明式配置解析（atomic-relay §2 schema + public-api §6）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..types import (
    RoleConfig,
    ScenarioConfig,
    SelectConfig,
    StopConfig,
    SummaryConfig,
)
from .validator import validate_config


def parse_config(raw: dict[str, Any], known_capabilities: set[str] | None = None) -> ScenarioConfig:
    """YAML 映射 → ScenarioConfig（解析 + 校验，非法即 raise）。"""
    config = ScenarioConfig(
        scenario=str(raw.get("scenario", "")),
        roles=[_parse_role(r) for r in raw.get("roles", [])],
        select=_parse_select(raw.get("select")),
        stop=_parse_stop(raw.get("stop")),
        summary=_parse_summary(raw.get("summary")),
    )
    validate_config(config, known_capabilities)
    return config


def load_config(path: str | Path, known_capabilities: set[str] | None = None) -> ScenarioConfig:
    """从 YAML 文件读 + 解析 + 校验。"""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return parse_config(raw, known_capabilities)


def _parse_role(raw: dict[str, Any]) -> RoleConfig:
    return RoleConfig(
        id=str(raw.get("id", "")),
        prompt=str(raw.get("prompt", "")),
        inject=list(raw.get("inject") or []),
        window=int(raw.get("window") or 0),
        output=raw.get("output", "free_text"),
    )


def _parse_select(raw: dict[str, Any] | None) -> SelectConfig:
    raw = raw or {}
    return SelectConfig(type=raw.get("type", "round_robin"), role=raw.get("role"))


def _parse_stop(raw: dict[str, Any] | None) -> StopConfig:
    raw = raw or {}
    return StopConfig(type=raw.get("type", "manual"), max=raw.get("max"), judge=raw.get("judge"))


def _parse_summary(raw: dict[str, Any] | None) -> SummaryConfig | None:
    if not raw:
        return None
    return SummaryConfig(
        role=str(raw.get("role", "")),
        key=str(raw.get("key", "")),
        window=int(raw.get("window") or 20),
    )
