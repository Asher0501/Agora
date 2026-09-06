"""LLM 适配 — 把 weave_agent_sdk 的 BaseLLM 适配到 agora 的 ``LLM.complete``。

weave_agent_sdk 的 BaseLLM 是 ``async chat(messages) -> LLMResponse``（deepseek /
anthropic / openai 经 ``factory.create_llm`` 可插拔）；agora 的 ``LLM`` 原子只需
``async complete(prompt) -> str``。本模块做薄适配，另提供离线 ``FakeLLM``
（确定性、不触网）供测试与离线运行（spec §6）。
"""
from __future__ import annotations

from typing import Any

from weave_agent_sdk.types import Message


class BaseLLM:
    """把 weave_agent_sdk 的 BaseLLM 适配到 agora ``LLM.complete`` 协议。"""

    def __init__(self, weave_llm: Any):
        self._llm = weave_llm

    async def complete(self, prompt: str) -> str:
        resp = await self._llm.chat([Message(role="user", content=prompt)])
        return resp.content


class FakeLLM:
    """确定性离线 LLM 双——返回固定文本，永不触网。"""

    def __init__(self, reply: str = "离线回复"):
        self._reply = reply

    async def complete(self, prompt: str) -> str:
        return self._reply
