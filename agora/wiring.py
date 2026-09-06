"""DI 装配（内部模块，public-api 模块地图不列它）。

装配 Repository + LLM + 扩展 registry，提供「create_run → relay」的一键装配
（镜像 brainstorm ``wiring.py``）。闭集菜单原子由 relay 直接构建；registry 的
``capabilities`` 只承载扩展区注册的自定义能力。
"""
from __future__ import annotations

from typing import Any

from .adapter.llm import FakeLLM
from .adapter.repository import Repository
from .extension import known_capabilities


class Registry:
    """DI 容器：LLM + 扩展能力 + 进度观察者（供 relay/session 消费）。"""

    def __init__(
        self,
        llm: Any | None = None,
        capabilities: dict[str, Any] | None = None,
        observers: list[Any] | None = None,
    ):
        self.llm = llm if llm is not None else FakeLLM()
        self.capabilities = dict(capabilities or {})
        self.observers = list(observers or [])

    def known_capabilities(self) -> set[str]:
        return known_capabilities(self.capabilities)


def build_registry(
    llm: Any | None = None,
    capabilities: dict[str, Any] | None = None,
    observers: list[Any] | None = None,
) -> Registry:
    """装配 registry（LLM + 扩展能力 + 观察者）。"""
    return Registry(llm=llm, capabilities=capabilities, observers=observers)


def build_repository(db_path: str) -> Repository:
    """装配 SQLite 持久化适配（唯一 weave_agent_sdk 集成点）。"""
    return Repository(db_path)


async def run_scenario(
    repository: Any,
    scenario: Any,
    runtime: Any,
    registry: Registry | None = None,
) -> Any:
    """一键装配：create_run → relay（供 SDK 用户与 CLI 复用）。"""
    from .relay import relay
    from .session import create_run

    reg = registry if registry is not None else build_registry()
    run = await create_run(repository, scenario, runtime, reg.known_capabilities())
    return await relay(repository, reg, run.run_id)
