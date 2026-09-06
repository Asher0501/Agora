"""声明式配置解析（atomic-relay §2 schema + public-api §6）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..types import (
    RoleConfig,
    RuntimeValues,
    ScenarioConfig,
    SelectConfig,
    StopConfig,
    SummaryConfig,
)
from .validator import validate_config


def parse_config(raw: dict[str, Any], known_capabilities: set[str] | None = None) -> ScenarioConfig:
    """YAML 映射 → ScenarioConfig（解析 + 校验，非法即 raise）。"""
    config = _build_scenario(raw)
    validate_config(config, known_capabilities)
    return config


def _build_scenario(raw: dict[str, Any]) -> ScenarioConfig:
    """纯解析（不校验），供 ``parse_config`` 与快照反序列化共用。"""
    return ScenarioConfig(
        scenario=str(raw.get("scenario", "")),
        roles=[_parse_role(r) for r in raw.get("roles", [])],
        select=_parse_select(raw.get("select")),
        stop=_parse_stop(raw.get("stop")),
        summary=_parse_summary(raw.get("summary")),
    )


# ── 快照序列化（T7 relay 读 / T8 session 写，ADR-0006 配置快照）───────


def scenario_to_dict(config: ScenarioConfig) -> dict[str, Any]:
    """ScenarioConfig → 快照 dict（key 与 dataclass 字段一致）。"""
    return {
        "scenario": config.scenario,
        "roles": [
            {"id": r.id, "prompt": r.prompt, "inject": r.inject, "window": r.window, "output": r.output}
            for r in config.roles
        ],
        "select": {"type": config.select.type, "role": config.select.role},
        "stop": {"type": config.stop.type, "max": config.stop.max, "judge": config.stop.judge},
        "summary": (
            {"role": config.summary.role, "key": config.summary.key, "window": config.summary.window}
            if config.summary
            else None
        ),
    }


def scenario_from_dict(raw: dict[str, Any]) -> ScenarioConfig:
    """快照 dict → ScenarioConfig（不校验——快照在 create 时已校验）。"""
    return _build_scenario(raw)


def runtime_to_dict(runtime: RuntimeValues) -> dict[str, Any]:
    return {"topic": runtime.topic, "stance": runtime.stance, "extra": runtime.extra}


def runtime_from_dict(raw: dict[str, Any]) -> RuntimeValues:
    return RuntimeValues(
        topic=str(raw.get("topic", "")),
        stance=raw.get("stance"),
        extra=dict(raw.get("extra") or {}),
    )


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
