"""Shared-table read — namespace-scoped, cross-session reads rejected (AC-05/AC-06b)."""
from __future__ import annotations

from typing import Any

from ..business.errors import NOT_FOUND, DomainError
from ..business.types import Speech


async def read_table(repository: Any, session_id: str) -> list[Speech]:
    """Return the session's shared table, seq-ordered; reject unknown sessions."""
    if await repository.load_session_config(session_id) is None:
        raise DomainError(NOT_FOUND, f"会话 {session_id} 不存在")
    return await repository.read_table(session_id)
