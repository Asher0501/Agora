"""Persona generation + private memory — the weave integration for roles.

``PersonaRole`` implements the ``Role`` protocol on top of weave's ``BaseLLM``;
``FakeLLM`` is the deterministic offline double used in tests and offline runs;
``PersonaPrivateMemory`` backs the ``RoleContext.private_memory`` handle (ADR-0006).
"""
from __future__ import annotations

import re
from typing import Any

from weave.llm.base import BaseLLM, LLMResponse
from weave.types import Message

from ..business.protocols import RoleContext
from ..business.types import Speech


class FakeLLM(BaseLLM):
    """Deterministic offline LLM double — echoes the topic + history window."""

    async def chat(self, messages, tools=None, max_tokens=4096, temperature=0.7) -> LLMResponse:
        system = next((m.content for m in messages if m.role == "system"), "")
        user = next((m.content for m in messages if m.role == "user"), "")
        name = _extract(system, r"你是(.+?)，") or "persona"
        topic = _extract(system, r"主题：「(.+?)」") or ""
        history = _parse_history(user)
        if history:
            last_speaker, last_text = history[-1]
            remark = f"承接 {last_speaker} 的「{last_text}」"
        else:
            remark = "开启讨论"
        content = f"[{name}] 针对「{topic}」：{remark}（共 {len(history)} 条历史发言）。"
        return LLMResponse(content=content)

    async def chat_stream(self, messages, tools=None, max_tokens=4096, temperature=0.7):
        resp = await self.chat(messages, tools, max_tokens, temperature)
        for ch in resp.content:
            yield ch


class PersonaRole:
    """A persona that produces a speech, injecting the topic + windowed history."""

    def __init__(
        self,
        persona_id: str,
        name: str,
        role_description: str,
        llm: BaseLLM,
        window_size: int = 20,
    ):
        self.persona_id = persona_id
        self.name = name
        self.role_description = role_description
        self._llm = llm
        self.window_size = window_size

    async def speak(self, ctx: RoleContext) -> str:
        history = ctx.history[-self.window_size :]
        messages = self._build_messages(ctx.topic, history)
        resp = await self._llm.chat(messages)
        return resp.content

    def _build_messages(self, topic: str, history: list[Speech]) -> list[Message]:
        system = (
            f"你是 {self.name}，人设定位：{self.role_description}。"
            f"当前头脑风暴主题：「{topic}」。"
        )
        history_block = "\n".join(f"{s.speaker_id}: {s.text}" for s in history)
        user = f"历史发言（最近 {len(history)} 条）：\n{history_block}"
        return [Message(role="system", content=system), Message(role="user", content=user)]


class PersonaPrivateMemory:
    """A persona-private memory handle backed by the repository (ADR-0006)."""

    def __init__(self, repository: Any, session_id: str, persona_id: str):
        self._repo = repository
        self._session_id = session_id
        self._persona_id = persona_id

    async def read(self, key: str) -> Any | None:
        return await self._repo.read_private(self._session_id, self._persona_id, key)

    async def write(self, key: str, value: Any) -> None:
        await self._repo.write_private(self._session_id, self._persona_id, key, value)


def _extract(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else None


def _parse_history(user: str) -> list[tuple[str, str]]:
    result = []
    for line in user.splitlines()[1:]:  # skip the header line
        if ":" in line:
            speaker, text = line.split(":", 1)
            result.append((speaker.strip(), text.strip()))
    return result
