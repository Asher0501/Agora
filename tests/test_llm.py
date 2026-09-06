"""T4 — LLM 适配（BaseLLM + FakeLLM，离线不触网）。"""
from __future__ import annotations

import pytest

from agora.adapter.llm import BaseLLM, FakeLLM


class _Resp:
    content = "真实回复"


class _FakeWeaveLLM:
    async def chat(self, messages, tools=None, max_tokens=4096, temperature=0.7):
        return _Resp()


@pytest.mark.asyncio
async def test_base_llm_adapts_weave_llm():
    adapter = BaseLLM(_FakeWeaveLLM())
    assert await adapter.complete("任意 prompt") == "真实回复"


@pytest.mark.asyncio
async def test_fake_llm_is_deterministic_and_offline():
    a = FakeLLM()
    assert await a.complete("x") == await a.complete("x")
    assert await a.complete("任意输入") == "离线回复"


@pytest.mark.asyncio
async def test_fake_llm_injectable_reply():
    fake = FakeLLM(reply="自定义")
    assert await fake.complete("whatever") == "自定义"
