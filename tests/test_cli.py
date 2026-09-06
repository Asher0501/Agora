"""T10 — CLI run/stop/resume/observe + 退出码（contracts/cli.md）。"""
from __future__ import annotations

import asyncio

import pytest
import yaml

from agora.adapter.llm import FakeLLM
from agora.adapter.repository import Repository
from agora.cli import main
from agora.session import create_run
from agora.types import RoleConfig, RuntimeValues, ScenarioConfig, SelectConfig, StopConfig


@pytest.fixture
def db(tmp_path):
    return str(tmp_path / "agora.db")


def _scenario_file(tmp_path, stop_type="fixed_rounds", stop_max=2):
    p = tmp_path / "scenario.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "scenario": "brainstorm",
                "roles": [
                    {"id": "alice", "prompt": "你是{name}。主题：{topic}", "inject": ["topic"], "output": "free_text"},
                    {"id": "bob", "prompt": "你是{name}。主题：{topic}", "inject": ["topic"], "output": "free_text"},
                ],
                "select": {"type": "round_robin"},
                "stop": {"type": stop_type, "max": stop_max},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return str(p)


def test_run_prints_run_id_and_outcome(capsys, db, tmp_path):
    rc = main(["run", "--config", _scenario_file(tmp_path), "--topic", "主题", "--db", db], llm_factory=FakeLLM)
    out = capsys.readouterr().out
    assert rc == 0
    assert "status=stopped" in out
    assert "termination=fixed_rounds" in out
    assert "turns=2" in out


def test_run_missing_topic_exit_1(capsys, db, tmp_path):
    rc = main(["run", "--config", _scenario_file(tmp_path), "--db", db], llm_factory=FakeLLM)
    err = capsys.readouterr().err
    assert rc == 1
    assert "agora.runtime_value_required" in err


def test_run_nonexistent_scenario_exit_1(capsys, db, tmp_path):
    rc = main(["run", "--config", str(tmp_path / "nope.yaml"), "--topic", "主题", "--db", db], llm_factory=FakeLLM)
    err = capsys.readouterr().err
    assert rc == 1
    assert "agora.scenario_not_found" in err


def test_stop_nonexistent_exit_1(capsys, db):
    rc = main(["stop", "nope", "--db", db], llm_factory=FakeLLM)
    assert rc == 1
    assert "agora.run_not_found" in capsys.readouterr().err


def test_resume_nonexistent_exit_1(capsys, db):
    rc = main(["resume", "nope", "--db", db], llm_factory=FakeLLM)
    assert rc == 1
    assert "agora.run_not_found" in capsys.readouterr().err


def test_observe_nonexistent_exit_1(capsys, db):
    rc = main(["observe", "nope", "--db", db], llm_factory=FakeLLM)
    assert rc == 1
    assert "agora.run_not_found" in capsys.readouterr().err


def test_observe_prints_persisted_events(capsys, db):
    run_id = asyncio.run(_seed_run_with_event(db))
    rc = main(["observe", run_id, "--db", db], llm_factory=FakeLLM)
    out = capsys.readouterr().out
    assert rc == 0
    assert "invalid_choice" in out
    assert "ghost" in out


async def _seed_run_with_event(db: str) -> str:
    repo = Repository(db)
    scenario = ScenarioConfig(
        scenario="brainstorm",
        roles=[
            RoleConfig(id="a", prompt="你是{name}。主题：{topic}", inject=["topic"], output="free_text"),
        ],
        select=SelectConfig(type="round_robin"),
        stop=StopConfig(type="manual"),
    )
    run = await create_run(repo, scenario, RuntimeValues(topic="主题"))
    await repo.append_event(
        run.run_id, {"type": "invalid_choice", "agent_id": "ghost", "reason": "选定的下一位不在名单内"}
    )
    repo.close()
    return run.run_id


def test_usage_error_exit_2(capsys, db):
    assert main(["bogus", "--db", db], llm_factory=FakeLLM) == 2
