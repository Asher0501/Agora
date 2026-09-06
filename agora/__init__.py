"""agora — semantics-free multi-agent relay engine（public-api §1 模块地图）。

把「多角色按序接力 + 共享转录 + 判停 + 持久化恢复」内核抽成无语义包。
公开表面：types / errors / namespaces / atoms / relay / session / config /
extension（adapter 是唯一 weave_agent_sdk 集成点，不导出）。
"""
from . import atoms, config, errors, extension, namespaces, relay, session, types

__all__ = [
    "atoms",
    "config",
    "errors",
    "extension",
    "namespaces",
    "relay",
    "session",
    "types",
]
