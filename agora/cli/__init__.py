"""CLI 驱动器（contracts/cli.md）：run / stop / resume / observe。

本地单进程，无鉴权、无幂等键、无重试/死信（sad §6 flagged items）。零引擎代码：
``run`` 走纯配置路径；菜单外能力经扩展区注册（T6），CLI 不新增命令。
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

from ..adapter.llm import FakeLLM
from ..adapter.repository import Repository
from ..config.schema import load_config
from ..errors import SCENARIO_NOT_FOUND, DomainError
from ..relay import relay
from ..session import create_run, resume_run, stop_run
from ..types import RuntimeValues

DEFAULT_DB = "./agora.db"


class _UsageError(Exception):
    """CLI 用法错误 → 退出码 2。"""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:
        raise _UsageError(message)


class _Registry:
    """DI 容器：LLM + 扩展能力 + 进度观察者（wiring.py 在 T11 形式化）。"""

    def __init__(self, llm: Any):
        self.llm = llm
        self.capabilities: dict[str, Any] = {}
        self.observers: list[Any] = []


def _reconfigure_stdio() -> None:
    """Windows 控制台强制 UTF-8（中文不因 cp1252 乱码）。"""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="agora")
    common = _ArgumentParser(add_help=False)
    common.add_argument("--db", default=None, help="SQLite 库路径（默认 ./agora.db）")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", parents=[common], help="启动并跑完一场会话")
    run.add_argument("--config", required=True, help="场景 YAML（roles/select/stop/summary）")
    run.add_argument("--topic", default=None, help="运行时值：主题（AC-02b 缺主题拒绝启动）")
    run.add_argument("--stance", default=None, help="运行时值：立场（辩论场景注入）")

    stop = sub.add_parser("stop", parents=[common], help="手动停止")
    stop.add_argument("run_id")

    resume = sub.add_parser("resume", parents=[common], help="恢复中断的会话")
    resume.add_argument("run_id")

    observe = sub.add_parser("observe", parents=[common], help="打印本会话事件")
    observe.add_argument("run_id")
    return parser


def main(argv: list[str] | None = None, *, llm_factory: Any = FakeLLM) -> int:
    """入口点；返回进程退出码。"""
    _reconfigure_stdio()
    try:
        args = build_parser().parse_args(argv)
    except _UsageError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        return asyncio.run(_dispatch(args, args.db or DEFAULT_DB, llm_factory))
    except _UsageError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except DomainError as exc:
        print(f"错误：{exc.message}（{exc.code}）", file=sys.stderr)
        return 1


async def _dispatch(args: argparse.Namespace, db: str, llm_factory: Any) -> int:
    repository = Repository(db)
    registry = _Registry(llm_factory())
    try:
        if args.command == "run":
            await _cmd_run(repository, registry, args)
        elif args.command == "stop":
            await _cmd_stop(repository, registry, args.run_id)
        elif args.command == "resume":
            await _cmd_resume(repository, registry, args.run_id)
        elif args.command == "observe":
            await _cmd_observe(repository, args.run_id)
        else:
            return 2
        return 0
    finally:
        repository.close()


async def _cmd_run(repository: Any, registry: Any, args: argparse.Namespace) -> None:
    try:
        scenario = load_config(args.config)
    except FileNotFoundError as exc:
        raise DomainError(SCENARIO_NOT_FOUND, f"场景文件 {args.config} 不存在") from exc
    run = await create_run(repository, scenario, RuntimeValues(topic=args.topic or "", stance=args.stance))
    print(run.run_id)
    outcome = await relay(repository, registry, run.run_id)
    _print_outcome(outcome)


async def _cmd_stop(repository: Any, registry: Any, run_id: str) -> None:
    _print_outcome(await stop_run(repository, registry, run_id))


async def _cmd_resume(repository: Any, registry: Any, run_id: str) -> None:
    run = await resume_run(repository, run_id)
    print(run.run_id)
    outcome = await relay(repository, registry, run_id)
    _print_outcome(outcome)


async def _cmd_observe(repository: Any, run_id: str) -> None:
    await resume_run(repository, run_id)  # 不存在 → run_not_found（退出 1）
    for event in await repository.read_events(run_id):
        print(f"{event.get('type')} {event.get('agent_id', '')} {event.get('reason', '')}")


def _print_outcome(outcome: Any) -> None:
    verdict = outcome.verdict
    print(
        f"status={outcome.status} termination={outcome.recap.termination} "
        f"converged={verdict.converged if verdict else False} "
        f"conclusion={verdict.conclusion if verdict else None} turns={len(outcome.transcript)}"
    )
