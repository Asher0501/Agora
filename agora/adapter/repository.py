"""SQLite Repository 适配 — 唯一 weave_agent_sdk 集成点。

把领域实体（Run / Turn / Agent 私有状态 / 系统事件）映射到 weave_agent_sdk 的
``memory_entries`` 单表（namespace + access_type + key），无 schema change
（data-model §Physical table）。跨会话/角色隔离（AC-16/17）由 namespace 构造
保证——越界查询在存储层即不可见。

``seq`` 在应用层分配（``max(existing seq) + 1``），非 DB 自增，保证追加顺序
不变量（QG-1）崩溃恢复后仍成立（ADR-0006）。

注：weave_agent_sdk 的 Memory API 是**同步**的（``stream.append/last``、
``state.get/set``），本类以 async 方法包裹之，使上层 relay/session 的 async
编排无需感知（本地单进程，SQLite 调用开销可忽略）。
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from weave_agent_sdk.memory.manager import MemoryManager
from weave_agent_sdk.types import MemoryConfig

from ..errors import TURN_ALREADY_PRODUCED, DomainError
from ..namespaces import (
    STATE_KEY_CONFIG,
    STATE_KEY_RECAP,
    STATE_KEY_STATUS,
    STATE_KEY_VERDICT,
    agent_state_ns,
    run_events_ns,
    run_state_ns,
    run_stream_ns,
)
from ..types import Turn

# 读「全部 stream 行」的上界。会话有界（几十到几百条发言），此值即「全部」。
_READ_ALL = 10**9


class Repository:
    """weave_agent_sdk 持久化适配（单 SQLite 库，跨 run 共享）。"""

    def __init__(self, db_path: str | Path):
        self._memory = MemoryManager(
            MemoryConfig(default_backend="sqlite", default_path=str(db_path))
        )

    # ── run 状态（config / status / verdict / recap）───────────────────

    async def save_config(self, run_id: str, config: dict[str, Any]) -> None:
        self._memory.state.set(STATE_KEY_CONFIG, config, run_state_ns(run_id))

    async def load_config(self, run_id: str) -> dict[str, Any] | None:
        return self._memory.state.get(STATE_KEY_CONFIG, run_state_ns(run_id))

    async def save_status(self, run_id: str, status: dict[str, Any]) -> None:
        self._memory.state.set(STATE_KEY_STATUS, status, run_state_ns(run_id))

    async def load_status(self, run_id: str) -> dict[str, Any] | None:
        return self._memory.state.get(STATE_KEY_STATUS, run_state_ns(run_id))

    async def save_verdict(self, run_id: str, verdict: dict[str, Any]) -> None:
        self._memory.state.set(STATE_KEY_VERDICT, verdict, run_state_ns(run_id))

    async def load_verdict(self, run_id: str) -> dict[str, Any] | None:
        return self._memory.state.get(STATE_KEY_VERDICT, run_state_ns(run_id))

    async def save_recap(self, run_id: str, recap: dict[str, Any]) -> None:
        self._memory.state.set(STATE_KEY_RECAP, recap, run_state_ns(run_id))

    async def load_recap(self, run_id: str) -> dict[str, Any] | None:
        return self._memory.state.get(STATE_KEY_RECAP, run_state_ns(run_id))

    # ── 共享转录（append-only，按 seq 有序）────────────────────────────

    async def append_turn(
        self, run_id: str, agent_id: str, text: str, seq: int | None = None
    ) -> Turn:
        """追加一条发言，``seq`` 为严格单调的 ``max(existing)+1``（缺省）或显式指定。

        AC-06（每 turn 恰好一条，Flow 6）：显式 ``seq`` 且该 turn 已落桌 → 抛
        ``TURN_ALREADY_PRODUCED``，不产生第二条。缺省 ``seq`` 由 ``max+1`` 保证
        单调、天然不重复；显式路径用于守卫并发/二次产出的重入。
        """
        if seq is None:
            recent = self._memory.stream.last(1, [run_stream_ns(run_id)])
            seq = (recent[0]["seq"] + 1) if recent else 1
        else:
            existing = self._memory.stream.last(_READ_ALL, [run_stream_ns(run_id)])
            if any(int(e["seq"]) == seq for e in existing):
                raise DomainError(
                    TURN_ALREADY_PRODUCED, f"turn {seq} 已产出，拒绝同 turn 二次产出"
                )
        now = time.time()
        entry = {"seq": seq, "agent_id": agent_id, "text": text, "created_at": now}
        self._memory.stream.append(entry, run_stream_ns(run_id))
        return Turn(run_id=run_id, seq=seq, agent_id=agent_id, text=text, created_at=now)

    async def read_transcript(self, run_id: str) -> list[Turn]:
        """返回完整共享转录，按 ``seq`` 升序（应用层排序，data-model §Indexes）。"""
        entries = self._memory.stream.last(_READ_ALL, [run_stream_ns(run_id)])
        turns = [
            Turn(
                run_id=run_id,
                seq=int(e["seq"]),
                agent_id=e["agent_id"],
                text=e["text"],
                created_at=float(e.get("created_at", 0.0)),
            )
            for e in entries
        ]
        turns.sort(key=lambda t: t.seq)
        return turns

    # ── agent 私有状态（AC-16/17 结构性隔离）──────────────────────────

    async def write_private(self, run_id: str, agent_id: str, key: str, value: Any) -> None:
        self._memory.state.set(key, value, agent_state_ns(run_id, agent_id))

    async def read_private(self, run_id: str, agent_id: str, key: str) -> Any | None:
        return self._memory.state.get(key, agent_state_ns(run_id, agent_id))

    # ── 系统观测事件（非转录）─────────────────────────────────────────

    async def append_event(self, run_id: str, event: dict[str, Any]) -> None:
        """落盘一条系统观测事件（invalid_choice / verdict_parse_failure）。"""
        self._memory.stream.append(event, run_events_ns(run_id))

    async def read_events(self, run_id: str) -> list[dict[str, Any]]:
        return self._memory.stream.last(_READ_ALL, [run_events_ns(run_id)])

    # ── 生命周期 ───────────────────────────────────────────────────────

    def close(self) -> None:
        self._memory.close()
