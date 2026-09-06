"""扩展区（受控逃生门，ADR-0004）。

菜单之外、确需自定义代码的能力走这里：``register_capability`` 把一个自定义
selector/terminator/summarizer 等登记进 registry，先注册、后加载（ADR-0005），
校验器的「已知能力」= 闭集菜单 ∪ registry 键。信任边界：同进程、视为受信代码，
读范围以 AC-16/17 为界（不跨 namespace）。本轮不承诺稳定/版本化 ABI。
"""
from __future__ import annotations

from typing import Any

from .atoms import MENU


def _capabilities_dict(registry: Any) -> dict[str, Any]:
    """取 registry 的 ``capabilities`` 映射（兼容 ``Registry`` 容器或裸 ``dict``）。"""
    caps = getattr(registry, "capabilities", None)
    if caps is not None:
        return caps
    if isinstance(registry, dict):
        return registry
    raise TypeError(f"registry 必须是 Registry 容器或 dict（收到 {type(registry).__name__}）")


def register_capability(registry: Any, name: str, capability: Any) -> None:
    """登记一个自定义能力到 registry（``Registry`` 容器或普通 ``dict``）。"""
    _capabilities_dict(registry)[name] = capability


def known_capabilities(registry: Any | None = None) -> set[str]:
    """闭集菜单 ∪ 已注册扩展能力——喂给 T5 ``validate_config``。"""
    caps = _capabilities_dict(registry) if registry is not None else {}
    return set(MENU) | set(caps)
