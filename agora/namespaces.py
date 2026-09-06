"""中性命名空间构造（零 weave 依赖）— data-model.md §Namespace scheme.

weave_agent_sdk 把 namespace 的**最后一个** ``:``-分段解析为 access type
（stream / state / knowledge），因此每个构造器必须以合法 access type 结尾。
``events`` 是 run 作用域下的保留分段——``agent_id`` 不得取 ``"events"``。
"""
from __future__ import annotations

# run 状态 key（data-model §RUN State key）。
STATE_KEY_CONFIG = "config"
STATE_KEY_STATUS = "status"
STATE_KEY_VERDICT = "verdict"
STATE_KEY_RECAP = "recap"


def run_stream_ns(run_id: str) -> str:
    """共享转录（append-only）。"""
    return f"agora:{run_id}:stream"


def run_state_ns(run_id: str) -> str:
    """run 状态（config / status / verdict / recap）。"""
    return f"agora:{run_id}:state"


def run_events_ns(run_id: str) -> str:
    """系统观测事件（无效选择 / 裁判解析失败），与转录分道。"""
    return f"agora:{run_id}:events:stream"


def agent_stream_ns(run_id: str, agent_id: str) -> str:
    """agent 私有 append-only 便签。"""
    return f"agora:{run_id}:{agent_id}:stream"


def agent_state_ns(run_id: str, agent_id: str) -> str:
    """agent 私有 keyed 状态（摘要等）。"""
    return f"agora:{run_id}:{agent_id}:state"
