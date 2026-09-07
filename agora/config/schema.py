"""声明式配置解析（atomic-relay §2 schema + public-api §6）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..errors import INVALID_CONFIG, DomainError
from ..types import (
    RoleConfig,
    RuntimeValues,
    ScenarioConfig,
    SelectConfig,
    StopConfig,
    SummaryConfig,
)
from .validator import validate_config


def _coerce_int(value: Any, field: str, default: int = 0) -> int:
    """把整型字段（max / window）强转为 int；非整型抛可读的 ``DomainError``。

    YAML 可能把数字写成字符串（``"3"``）；接受纯数字字符串并强转，拒绝非数字
    （``"abc"`` / 浮点 / bool），保证加载时以 ``DomainError`` 拒绝而非裸
    ``TypeError``/``ValueError``（ADR-0005 / QG-1）。
    """
    if value is None:
        return default
    if isinstance(value, bool):
        raise DomainError(INVALID_CONFIG, f"{field} 必须为整数（收到 {value!r}）")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s.lstrip("-").isdigit():
            return int(s)
    raise DomainError(INVALID_CONFIG, f"{field} 必须为整数（收到 {value!r}）")


def parse_config(raw: dict[str, Any], known_capabilities: set[str] | None = None) -> ScenarioConfig:
    """YAML 映射 → ScenarioConfig（解析 + 校验，非法即 raise）。"""
    if not isinstance(raw, dict):
        raise DomainError(INVALID_CONFIG, f"配置必须为映射（收到 {type(raw).__name__}）")
    config = _build_scenario(raw)
    validate_config(config, known_capabilities)
    return config


def _build_scenario(raw: dict[str, Any]) -> ScenarioConfig:
    """纯解析（不校验），供 ``parse_config`` 与快照反序列化共用。"""
    roles_raw = raw.get("roles", [])
    if not isinstance(roles_raw, list):
        raise DomainError(INVALID_CONFIG, "roles 必须为列表")
    return ScenarioConfig(
        scenario=str(raw.get("scenario", "")),
        roles=[_parse_role(r) for r in roles_raw],
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
    if not isinstance(raw, dict):
        raise DomainError(INVALID_CONFIG, f"role 必须为映射（收到 {type(raw).__name__}）")
    output = raw.get("output", "free_text")
    if output not in {"free_text", "pick_next", "verdict"}:
        raise DomainError(
            INVALID_CONFIG,
            f"角色 {raw.get('id', '')} 的 output 非法：{output!r}（应为 free_text / pick_next / verdict）",
        )
    return RoleConfig(
        id=str(raw.get("id", "")),
        prompt=str(raw.get("prompt", "")),
        inject=list(raw.get("inject") or []),
        window=_coerce_int(raw.get("window"), "window", 0),
        output=output,
    )


def _parse_select(raw: dict[str, Any] | None) -> SelectConfig:
    if raw is None:
        raw = {}
    elif not isinstance(raw, dict):
        raise DomainError(INVALID_CONFIG, f"select 必须为映射（收到 {type(raw).__name__}）")
    return SelectConfig(type=raw.get("type", "round_robin"), role=raw.get("role"))


def _parse_stop(raw: dict[str, Any] | None) -> StopConfig:
    if raw is None:
        raw = {}
    elif not isinstance(raw, dict):
        raise DomainError(INVALID_CONFIG, f"stop 必须为映射（收到 {type(raw).__name__}）")
    raw_max = raw.get("max")
    return StopConfig(
        type=raw.get("type", "manual"),
        max=None if raw_max is None else _coerce_int(raw_max, "stop.max"),
        judge=raw.get("judge"),
    )


def _parse_summary(raw: dict[str, Any] | None) -> SummaryConfig | None:
    if not raw:
        return None
    if not isinstance(raw, dict):
        raise DomainError(INVALID_CONFIG, f"summary 必须为映射（收到 {type(raw).__name__}）")
    return SummaryConfig(
        role=str(raw.get("role", "")),
        key=str(raw.get("key", "")),
        window=_coerce_int(raw.get("window"), "summary.window", 20),
    )
