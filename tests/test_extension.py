"""T6 — 扩展区注册 register_capability（AC-14）。"""
from __future__ import annotations

import pytest

from agora.atoms import MENU
from agora.config import parse_config
from agora.errors import UNKNOWN_CAPABILITY, DomainError
from agora.extension import known_capabilities, register_capability


class _CustomSelector:
    """自定义选人能力（扩展区）。"""

    async def next(self, roster, transcript):
        return None


def _raw():
    return {
        "scenario": "brainstorm",
        "roles": [
            {"id": "alice", "prompt": "主题：{topic}", "inject": ["topic"], "output": "free_text"},
        ],
        "select": {"type": "round_robin"},
        "stop": {"type": "fixed_rounds", "max": 3},
    }


def test_register_capability_is_retrievable():
    registry = {}
    cap = _CustomSelector()
    register_capability(registry, "custom_sel", cap)
    assert registry["custom_sel"] is cap


def test_registered_capability_passes_validation():
    registry = {}
    register_capability(registry, "custom_sel", _CustomSelector())
    known = known_capabilities(registry)
    raw = _raw()
    raw["select"] = {"type": "custom_sel"}
    c = parse_config(raw, known_capabilities=known)
    assert c.select.type == "custom_sel"


def test_unregistered_capability_rejected():
    known = known_capabilities({})  # 菜单 only
    raw = _raw()
    raw["select"] = {"type": "custom_sel"}
    with pytest.raises(DomainError) as exc:
        parse_config(raw, known_capabilities=known)
    assert exc.value.code == UNKNOWN_CAPABILITY


def test_standard_menu_unaffected_by_extension():
    registry = {}
    register_capability(registry, "custom_sel", _CustomSelector())
    known = known_capabilities(registry)
    # 菜单仍是已知能力子集，标准配置照常通过
    assert MENU <= known
    c = parse_config(_raw(), known_capabilities=known)
    assert c.select.type == "round_robin"
    assert c.stop.type == "fixed_rounds"
