"""配置不变量校验（ADR-0005 加载时校验，US-07 / AC-03/04/13）。

「已知能力」= 闭集菜单 ∪ 已注册扩展（扩展先注册后加载）。非法配置 100%
加载时被拒并给出可读原因。校验器只依赖 ``known_capabilities: set[str]``，
不 import extension 模块（与 T6 并行无耦合）。
"""
from __future__ import annotations

import re

from ..atoms import MENU
from ..errors import (
    INVALID_CONFIG,
    INVALID_PLACEHOLDER,
    OUTPUT_JUDGE_MISMATCH,
    RESERVED_AGENT_ID,
    ROLE_DESCRIPTION_REQUIRED,
    UNKNOWN_CAPABILITY,
    DomainError,
)
from ..types import RoleConfig, ScenarioConfig

# 可注入的上下文字段名（atomic-relay §2 占位符）。
_KNOWN_FIELDS = frozenset({"name", "role_description", "topic", "stance", "history"})
# 身份字段：总是可用（不要求在 inject 里声明）。
_IDENTITY = frozenset({"name", "role_description"})
# 保留字：与系统事件 namespace（agora:{run_id}:events:stream）撞名。
_RESERVED_AGENT_IDS = frozenset({"events"})

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def validate_config(config: ScenarioConfig, known_capabilities: set[str] | None = None) -> None:
    """校验场景配置不变量；非法即 ``raise DomainError``。

    ``known_capabilities`` 缺省为闭集菜单 ``MENU``；扩展区（T6）注入菜单 ∪ registry。
    """
    known = known_capabilities or MENU

    # AC-03：选人/判停方式 ∈ 菜单 ∪ 已注册扩展
    if config.select.type not in known:
        raise DomainError(UNKNOWN_CAPABILITY, f"选人方式 {config.select.type} 不受支持")
    if config.stop.type not in known:
        raise DomainError(UNKNOWN_CAPABILITY, f"判停方式 {config.stop.type} 不受支持")

    role_by_id = {r.id: r for r in config.roles}

    # 保留字：agent_id 不得为 `events`
    for role in config.roles:
        if role.id in _RESERVED_AGENT_IDS:
            raise DomainError(RESERVED_AGENT_ID, f"角色 id {role.id} 是保留字，不得使用")

    # AC-04：角色描述必填
    for role in config.roles:
        if not role.prompt or not role.prompt.strip():
            raise DomainError(ROLE_DESCRIPTION_REQUIRED, f"角色 {role.id} 缺少产出所需描述")

    # SummaryConfig 最小形状（api-sync-report §C-2，待 data-model ratify）
    identity = set(_IDENTITY)
    if config.summary is not None:
        if not config.summary.role or not config.summary.key:
            raise DomainError(INVALID_CONFIG, "summary 的 role 与 key 必填")
        if config.summary.role not in role_by_id:
            raise DomainError(INVALID_CONFIG, f"summary 的角色 {config.summary.role} 不在名单内")
        identity.add(config.summary.key)  # summary 注入字段始终可用

    # AC-13：output 与 select/stop 匹配
    if config.stop.type == "llm_verdict" and config.stop.judge:
        judge = role_by_id.get(config.stop.judge)
        if judge is None:
            raise DomainError(INVALID_CONFIG, f"裁判 {config.stop.judge} 不在角色名单内")
        if judge.output != "verdict":
            raise DomainError(
                OUTPUT_JUDGE_MISMATCH,
                f"裁判 {config.stop.judge} 的产出格式应为 verdict（当前为 {judge.output}）",
            )
    if config.select.type == "llm_pick" and config.select.role:
        picker = role_by_id.get(config.select.role)
        if picker is None:
            raise DomainError(INVALID_CONFIG, f"选人者 {config.select.role} 不在角色名单内")
        if picker.output != "pick_next":
            raise DomainError(
                OUTPUT_JUDGE_MISMATCH,
                f"选人者 {config.select.role} 的产出格式应为 pick_next（当前为 {picker.output}）",
            )

    # 模板占位符与 inject 字段名匹配
    for role in config.roles:
        _validate_placeholders(role, identity)

    # max / window 数值合法
    if config.stop.max is not None and config.stop.max <= 0:
        raise DomainError(INVALID_CONFIG, "stop.max 必须为正整数")
    for role in config.roles:
        if role.window < 0:
            raise DomainError(INVALID_CONFIG, f"角色 {role.id} 的 window 不能为负")


def _validate_placeholders(role: RoleConfig, identity: set[str]) -> None:
    inject = set(role.inject)
    for field in inject:
        if field not in _KNOWN_FIELDS and field not in identity:
            raise DomainError(INVALID_PLACEHOLDER, f"角色 {role.id} 的 inject 含未知字段 {field}")
    for placeholder in _PLACEHOLDER_RE.findall(role.prompt):
        if placeholder not in identity and placeholder not in inject:
            raise DomainError(
                INVALID_PLACEHOLDER,
                f"角色 {role.id} 的模板占位符 {{{placeholder}}} 未在 inject 中声明",
            )
