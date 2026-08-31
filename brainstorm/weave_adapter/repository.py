"""Persistence repository — the single weave integration point for storage.

Maps the logical entities (Session / Speech / private memory / system events) onto
weave's ``memory_entries`` table via ``namespace + access_type + key``
(data-model.md §Entities). All reads/writes go through weave's ``MemoryManager``;
the rest of the engine never touches weave directly.

``seq`` is allocated at the application layer as ``max(existing seq) + 1`` — not a
DB auto-increment — so the append-order invariant (QG-1) holds even after a crash
and resume (ADR-0003).
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from weave.memory.manager import MemoryManager
from weave.types import MemoryConfig

from ..business.namespaces import (
    STATE_KEY_CONCLUSION,
    STATE_KEY_CONFIG,
    STATE_KEY_STATUS,
    persona_state_ns,
    session_events_ns,
    session_state_ns,
    session_stream_ns,
)
from ..business.types import Speech

# Upper bound for a "read every stream row" query. Sessions are bounded (a
# brainstorm is dozens-to-hundreds of speeches), so this is effectively "all".
_READ_ALL = 10**9


class Repository:
    """Weave-backed persistence for one SQLite store (shared across sessions)."""

    def __init__(self, db_path: str | Path):
        self._memory = MemoryManager(
            MemoryConfig(default_backend="sqlite", default_path=str(db_path))
        )

    # ── session state ───────────────────────────────────────

    async def save_session_config(self, session_id: str, config: dict[str, Any]) -> None:
        await self._memory.state.set(
            STATE_KEY_CONFIG, config, session_state_ns(session_id)
        )

    async def load_session_config(self, session_id: str) -> dict[str, Any] | None:
        return await self._memory.state.get(STATE_KEY_CONFIG, session_state_ns(session_id))

    async def update_session_status(self, session_id: str, status: dict[str, Any]) -> None:
        await self._memory.state.set(
            STATE_KEY_STATUS, status, session_state_ns(session_id)
        )

    async def load_session_status(self, session_id: str) -> dict[str, Any] | None:
        return await self._memory.state.get(STATE_KEY_STATUS, session_state_ns(session_id))

    async def write_conclusion(self, session_id: str, conclusion: dict[str, Any]) -> None:
        await self._memory.state.set(
            STATE_KEY_CONCLUSION, conclusion, session_state_ns(session_id)
        )

    async def load_conclusion(self, session_id: str) -> dict[str, Any] | None:
        return await self._memory.state.get(
            STATE_KEY_CONCLUSION, session_state_ns(session_id)
        )

    # ── shared table ─────────────────────────────────────────

    async def append_speech(self, session_id: str, speaker_id: str, text: str) -> Speech:
        """Append a speech with the next strictly-monotonic ``seq``."""
        table = await self.read_table(session_id)
        seq = max((s.seq for s in table), default=0) + 1
        now = time.time()
        entry = {
            "seq": seq,
            "speaker_id": speaker_id,
            "text": text,
            "created_at": now,
        }
        await self._memory.stream.append(entry, session_stream_ns(session_id))
        return Speech(seq=seq, speaker_id=speaker_id, text=text, created_at=now)

    async def read_table(self, session_id: str) -> list[Speech]:
        """Return the full shared table, ordered by ``seq`` ascending (AC-05)."""
        entries = await self._memory.stream.last(_READ_ALL, [session_stream_ns(session_id)])
        speeches = [
            Speech(
                seq=e["seq"],
                speaker_id=e["speaker_id"],
                text=e["text"],
                created_at=float(e.get("created_at", 0.0)),
            )
            for e in entries
        ]
        speeches.sort(key=lambda s: s.seq)
        return speeches

    # ── private memory ───────────────────────────────────────

    async def write_private(self, session_id: str, persona_id: str, key: str, value: Any) -> None:
        await self._memory.state.set(
            key, value, persona_state_ns(session_id, persona_id)
        )

    async def read_private(self, session_id: str, persona_id: str, key: str) -> Any | None:
        return await self._memory.state.get(key, persona_state_ns(session_id, persona_id))

    # ── system events ────────────────────────────────────────

    async def append_event(self, session_id: str, event: dict[str, Any]) -> None:
        """Persist a system event (skip / invalid_choice) off the shared table."""
        await self._memory.stream.append(event, session_events_ns(session_id))

    async def read_events(self, session_id: str) -> list[dict[str, Any]]:
        """Read the session's system events (append order, oldest first)."""
        return await self._memory.stream.last(_READ_ALL, [session_events_ns(session_id)])

    # ── lifecycle ────────────────────────────────────────────

    def close(self) -> None:
        self._memory.close()
