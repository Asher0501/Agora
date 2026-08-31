"""Command-line driver — create / run / stop / export (contracts/cli.md)."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from ..business.errors import DomainError
from ..business.types import SessionConfig, StopConditionConfig
from ..config_loader import load_config, load_personas
from ..engine.loop import run_session
from ..engine.registry import Registry
from ..engine.session import create_session, resume_session
from ..engine.stop import stop_session
from ..engine.table import read_table
from ..extensions.schedulers.moderator import ModeratorScheduler
from ..extensions.stop_conditions.convergence import ConvergenceStop
from ..weave_adapter.persona_agent import FakeLLM, PersonaRole
from ..weave_adapter.repository import Repository
from ..wiring import assemble_defaults

DEFAULT_DB = "./brainstorm.db"
_WINDOW_SIZE = 20


class _UsageError(Exception):
    """A CLI usage error → exit code 2."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:
        raise _UsageError(message)


def _reconfigure_stdio() -> None:
    """Force UTF-8 on the console (Windows defaults to cp1252 → Chinese garbles)."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="brainstorm")
    common = _ArgumentParser(add_help=False)
    common.add_argument("--db", default=None, help="SQLite 库路径（默认 ./brainstorm.db）")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="创建会话", parents=[common])
    create.add_argument("--topic")
    create.add_argument("--personas")
    create.add_argument("--scheduler", default="round_robin")
    create.add_argument("--stop-condition", default="fixed_rounds")
    create.add_argument("--max-speeches", type=int)
    create.add_argument("--config")

    for name in ("run", "stop", "export"):
        p = sub.add_parser(name, parents=[common])
        p.add_argument("session_id")
        if name == "export":
            p.add_argument("--format", default="text", choices=("text", "json"))
    return parser


def main(argv: list[str] | None = None, *, db_path: str | None = None) -> int:
    """Entry point; returns the process exit code."""
    _reconfigure_stdio()
    try:
        args = build_parser().parse_args(argv)
    except _UsageError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        return asyncio.run(_dispatch(args, db_path or args.db or DEFAULT_DB))
    except _UsageError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except DomainError as exc:
        print(f"错误：{exc.message}（{exc.code}）", file=sys.stderr)
        return 1


async def _dispatch(args: argparse.Namespace, db: str) -> int:
    repository = Repository(db)
    registry = _build_registry()
    try:
        if args.command == "create":
            await _cmd_create(repository, registry, args)
        elif args.command == "run":
            await _cmd_run(repository, registry, args.session_id)
        elif args.command == "stop":
            await _cmd_stop(repository, registry, args.session_id)
        elif args.command == "export":
            await _cmd_export(repository, args.session_id, args.format)
        else:
            return 2
        return 0
    finally:
        repository.close()


def _build_registry() -> Registry:
    registry = Registry()
    assemble_defaults(registry)  # round_robin, fixed_rounds, manual
    registry.register_stop_condition("convergence", ConvergenceStop())
    return registry


# ── commands ──────────────────────────────────────────────

async def _cmd_create(repository: Any, registry: Registry, args: argparse.Namespace) -> None:
    config = _build_config(args)
    session = await create_session(repository, config)
    print(session.session_id)


def _build_config(args: argparse.Namespace) -> SessionConfig:
    if args.config is not None:
        if args.topic is not None or args.personas is not None:
            raise _UsageError("--config 与 --topic/--personas 互斥")
        return load_config(args.config)
    if args.topic is None or args.personas is None:
        raise _UsageError("需要 --topic 与 --personas（或使用 --config）")
    return SessionConfig(
        topic=args.topic,
        personas=load_personas(args.personas),
        scheduler=args.scheduler,
        stop_condition=StopConditionConfig(
            type=args.stop_condition, max_speeches=args.max_speeches
        ),
    )


async def _cmd_run(repository: Any, registry: Registry, session_id: str) -> None:
    session = await resume_session(repository, session_id)
    _register_roles(registry, session)
    outcome = await run_session(repository, registry, session_id)
    _print_outcome(outcome)


def _register_roles(registry: Registry, session: Any) -> None:
    for p in session.personas:
        registry.register_role(
            p.persona_id,
            PersonaRole(p.persona_id, p.name, p.role_description, FakeLLM(), _WINDOW_SIZE),
        )
    if session.scheduler == "moderator":
        router_id = session.personas[0].persona_id
        registry.register_scheduler("moderator", ModeratorScheduler(registry.get_role(router_id)))


async def _cmd_stop(repository: Any, registry: Registry, session_id: str) -> None:
    _print_outcome(await stop_session(repository, registry, session_id))


async def _cmd_export(repository: Any, session_id: str, fmt: str) -> None:
    speeches = await read_table(repository, session_id)
    if fmt == "json":
        print(
            json.dumps(
                [
                    {"seq": s.seq, "speaker_id": s.speaker_id, "text": s.text}
                    for s in speeches
                ],
                ensure_ascii=False,
            )
        )
    else:
        for s in speeches:
            print(f"{s.seq}. {s.speaker_id}: {s.text}")


def _print_outcome(outcome: Any) -> None:
    print(
        f"status={outcome.status} converged={outcome.converged} "
        f"conclusion={outcome.conclusion} speeches={len(outcome.speeches)}"
    )
