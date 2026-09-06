"""扩展区（受控逃生门，ADR-0004）。

菜单之外、确需自定义代码的能力走这里：``register_capability`` 把一个自定义
selector/terminator/summarizer 等登记进 registry，先注册、后加载（ADR-0005），
校验器的「已知能力」= 闭集菜单 ∪ registry 键。信任边界：同进程、视为受信代码，
读范围以 AC-16/17 为界（不跨 namespace）。本轮不承诺稳定/版本化 ABI。
"""
from __future__ import annotations

from typing import Any

from .atoms import MENU


def register_capability(registry: dict[str, Any], name: str, capability: Any) -> None:
    """登记一个自定义能力到 registry（普通 ``dict``，由 wiring 创建并注入校验/接力）。"""
    registry[name] = capability


def known_capabilities(registry: dict[str, Any] | None = None) -> set[str]:
    """闭集菜单 ∪ 已注册扩展能力——喂给 T5 ``validate_config``。"""
    return set(MENU) | (set(registry) if registry else set())
