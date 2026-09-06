"""会话生命周期（public-api §5）：create / resume / stop / read + subscribe。

create_run 定格配置快照（ADR-0006：scenario + runtime 折叠为不可变快照）；
resume_run 只读快照、不重读磁盘配置（AC-15）；stop_run 写停止标志 + 「手动停止」
recap（AC-11）；read_transcript 读本 run 转录（AC-16/17 隔离内的读路径）。
"""
from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from .config.schema import runtime_from_dict, runtime_to_dict, scenario_from_dict, scenario_to_dict
from .config.validator import validate_config
from .errors import (
    RUN_CORRUPTED,
    RUN_NOT_FOUND,
    RUNTIME_VALUE_REQUIRED,
    SCENARIO_NOT_FOUND,
    DomainError,
)
from .relay import ProgressEvent
from .types import Recap, Run, RunOutcome, RuntimeValues, ScenarioConfig, Turn


async def create_run(
    repository: Any,
    scenario: ScenarioConfig,
    runtime: RuntimeValues,
    known_capabilities: set[str] | None = None,
) -> Run:
    """校验（AC-02b/03/04/13）+ 快照 config（ADR-0006）+ 建 running Run（AC-02）。"""
    if not scenario.scenario or not scenario.scenario.strip():
        raise DomainError(SCENARIO_NOT_FOUND, "未指定场景")
    if not runtime.topic or not runtime.topic.strip():
        raise DomainError(RUNTIME_VALUE_REQUIRED, "主题不能为空")
    validate_config(scenario, known_capabilities)

    run_id = str(uuid4())
    now = time.time()
    snapshot = {
        "scenario": scenario_to_dict(scenario),
        "runtime": runtime_to_dict(runtime),
        "created_at": now,
    }
    await repository.save_config(run_id, snapshot)
    await repository.save_status(run_id, {"status": "running", "current_seq": 0, "last_agent_id": None})
    return Run(
        run_id=run_id,
        scenario=scenario,
        runtime=runtime,
        status="running",
        current_seq=0,
        created_at=now,
    )


async def resume_run(repository: Any, run_id: str) -> Run:
    """从快照 + 已落桌转录重建 Run（ADR-0006）；不存在/损坏即拒（AC-15b）。"""
    config = await repository.load_config(run_id)
    if config is None:
        raise DomainError(RUN_NOT_FOUND, f"会话 {run_id} 不存在")
    try:
        scenario = scenario_from_dict(config.get("scenario") or {})
        runtime = runtime_from_dict(config.get("runtime") or {})
    except Exception as exc:
        raise DomainError(RUN_CORRUPTED, f"会话 {run_id} 状态损坏") from exc
    status = await repository.load_status(run_id) or {}
    transcript = await repository.read_transcript(run_id)
    return Run(
        run_id=run_id,
        scenario=scenario,
        runtime=runtime,
        status=status.get("status", "running"),
        current_seq=len(transcript),  # 已落桌不重放（AC-15）
        created_at=float(config.get("created_at", 0.0)),
    )


async def stop_run(repository: Any, registry: Any, run_id: str) -> RunOutcome:
    """手动停止（AC-11）：写停止标志 + 「手动停止」recap；在途发言不落桌。"""
    if await repository.load_config(run_id) is None:
        raise DomainError(RUN_NOT_FOUND, f"会话 {run_id} 不存在")
    transcript = await repository.read_transcript(run_id)
    # 一次性写状态：置 stopped 的同时保留 stop_requested——运行中的 relay 轮询它，
    # 若被覆盖则接力永不终止（AC-11）。
    await repository.save_status(
        run_id,
        {
            "status": "stopped",
            "stop_requested": True,
            "current_seq": len(transcript),
            "last_agent_id": transcript[-1].agent_id if transcript else None,
        },
    )
    recap_text = f"本场接力共 {len(transcript)} 条发言，终止方式：manual（手动停止）"
    await repository.save_recap(run_id, {"termination": "manual", "recap": recap_text})
    _emit(registry, run_id, "run.stopped", {"status": "stopped"})
    return RunOutcome(
        run_id=run_id,
        status="stopped",
        verdict=None,
        recap=Recap(termination="manual", recap=recap_text),
        transcript=transcript,
    )


async def read_transcript(repository: Any, run_id: str) -> list[Turn]:
    """读本 run 共享转录（按 seq 升序；AC-16/17 隔离内的读路径）。"""
    if await repository.load_config(run_id) is None:
        raise DomainError(RUN_NOT_FOUND, f"会话 {run_id} 不存在")
    return await repository.read_transcript(run_id)


def subscribe(registry: Any, observer: Any) -> None:
    """订阅进度事件（AC-18 入口，进程内发布-订阅）。"""
    if not hasattr(registry, "observers"):
        registry.observers = []
    registry.observers.append(observer)


def _emit(registry: Any, run_id: str, name: str, payload: dict[str, Any]) -> None:
    for observer in getattr(registry, "observers", []):
        observer.on_event(ProgressEvent(name=name, run_id=run_id, payload=payload))
