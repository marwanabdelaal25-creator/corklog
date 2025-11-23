"""Tests for corklog.cli."""

import pytest

from corklog.cli import build_parser, main


def test_build_parser_has_init():
    p = build_parser()
    assert "init" in p._subparsers._group_actions[0].choices


def test_main_help():
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_init_creates_library(tmp_path):
    db = tmp_path / "lib.json"
    assert main(["--data", str(db), "init"]) == 0
    assert db.exists()


def test_bottle_add_and_list(tmp_path):
    db = tmp_path / "lib.json"
    main(["--data", str(db), "init"])
    rc = main(["--data", str(db), "bottle-add", "Snow Crash", "--status", "want"])
    assert rc == 0
    assert main(["--data", str(db), "bottle-list"]) == 0


def test_stats_empty_library(tmp_path):
    db = tmp_path / "lib.json"
    main(["--data", str(db), "init"])
    assert main(["--data", str(db), "stats"]) == 0


def test_lwin_check_valid():
    assert main(["lwin-check", "1011266"]) == 0


def test_lwin_check_invalid():
    assert main(["lwin-check", "not-an-id"]) == 1
