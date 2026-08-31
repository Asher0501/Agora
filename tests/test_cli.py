"""T11 — CLI create / run / stop / export + exit codes (contracts/cli.md)."""

import json

import pytest
import yaml

from brainstorm.cli import main


@pytest.fixture
def db(tmp_path):
    return str(tmp_path / "brainstorm.db")


def _personas_file(tmp_path):
    p = tmp_path / "personas.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "personas": [
                    {"persona_id": "a", "name": "A", "role_description": "产品"},
                    {"persona_id": "b", "name": "B", "role_description": "技术"},
                ]
            }
        ),
        encoding="utf-8",
    )
    return str(p)


def test_create_prints_session_id(capsys, db, tmp_path):
    rc = main(
        ["create", "--topic", "主题", "--personas", _personas_file(tmp_path)],
        db_path=db,
    )
    out = capsys.readouterr().out.strip()
    assert rc == 0
    assert out  # non-empty session_id


def test_run_prints_outcome(capsys, db, tmp_path):
    main(
        ["create", "--topic", "主题", "--personas", _personas_file(tmp_path), "--max-speeches", "2"],
        db_path=db,
    )
    session_id = capsys.readouterr().out.strip()

    rc = main(["run", session_id], db_path=db)
    out = capsys.readouterr().out

    assert rc == 0
    assert "status=stopped" in out
    assert "speeches=2" in out


def test_domain_error_exit_1(capsys, db, tmp_path):
    rc = main(
        ["create", "--topic", "", "--personas", _personas_file(tmp_path)],
        db_path=db,
    )
    err = capsys.readouterr().err
    assert rc == 1
    assert "session.topic_required" in err


def test_usage_error_exit_2(capsys, db):
    assert main(["bogus"], db_path=db) == 2


def test_config_xor_single_flags(capsys, db):
    assert main(["create", "--config", "x.yaml", "--topic", "主题"], db_path=db) == 2


def test_export_json(capsys, db, tmp_path):
    main(
        ["create", "--topic", "主题", "--personas", _personas_file(tmp_path), "--max-speeches", "2"],
        db_path=db,
    )
    sid = capsys.readouterr().out.strip()
    main(["run", sid], db_path=db)
    capsys.readouterr()

    rc = main(["export", sid, "--format", "json"], db_path=db)
    out = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert isinstance(out, list)
    assert len(out) == 2
    assert set(out[0]) == {"seq", "speaker_id", "text"}
