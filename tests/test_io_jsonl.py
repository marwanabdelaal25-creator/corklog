"""Tests for corklog.io_jsonl."""

import json
from pathlib import Path

import pytest
from corklog.bottle import Bottle
from corklog.tasting import Session
from corklog.errors import ExportError, ImportError as PTImportError
from corklog import io_jsonl


def test_export_jsonl_bottles(library_store, sample_bottle, tmp_path):
    library_store.upsert_bottle(sample_bottle)
    dest = tmp_path / "bottles.jsonl"
    n = io_jsonl.export_jsonl_bottles(library_store, dest)
    assert n == 1
    line = dest.read_text(encoding="utf-8").strip()
    assert json.loads(line)["title"] == sample_bottle.title


def test_export_jsonl_tastings(library_store, sample_bottle, sample_tasting, tmp_path):
    library_store.upsert_bottle(sample_bottle)
    library_store.tastings[sample_tasting.id] = sample_tasting
    dest = tmp_path / "sess.jsonl"
    n = io_jsonl.export_jsonl_tastings(library_store, dest)
    assert n == 1


def test_import_jsonl_bottles(library_store, sample_bottle, tmp_path):
    dest = tmp_path / "in.jsonl"
    dest.write_text(json.dumps(sample_bottle.to_dict()) + "\n", encoding="utf-8")
    n = io_jsonl.import_jsonl_bottles(library_store, dest)
    assert n == 1
    assert sample_bottle.id in library_store.bottles


def test_import_jsonl_missing(library_store, tmp_path):
    with pytest.raises(PTImportError):
        io_jsonl.import_jsonl_bottles(library_store, tmp_path / "nope.jsonl")


def test_import_jsonl_tastings(library_store, sample_tasting, tmp_path):
    dest = tmp_path / "s.jsonl"
    dest.write_text(json.dumps(sample_tasting.to_dict()) + "\n", encoding="utf-8")
    n = io_jsonl.import_jsonl_tastings(library_store, dest)
    assert n == 1
    assert sample_tasting.id in library_store.tastings


def test_iter_lines_skips_blank(tmp_path):
    p = tmp_path / "b.jsonl"
    p.write_text("line\n\n  \n", encoding="utf-8")
    lines = list(io_jsonl._iter_lines(p))
    assert lines == ["line"]


def test_export_empty_bottles(library_store, tmp_path):
    n = io_jsonl.export_jsonl_bottles(library_store, tmp_path / "e.jsonl")
    assert n == 0


def test_export_empty_tastings(library_store, tmp_path):
    n = io_jsonl.export_jsonl_tastings(library_store, tmp_path / "e.jsonl")
    assert n == 0


def test_import_multiple_bottles(library_store, tmp_path):
    b1 = Bottle.create("One")
    b2 = Bottle.create("Two")
    dest = tmp_path / "multi.jsonl"
    dest.write_text(
        json.dumps(b1.to_dict()) + "\n" + json.dumps(b2.to_dict()) + "\n",
        encoding="utf-8",
    )
    assert io_jsonl.import_jsonl_bottles(library_store, dest) == 2


def test_roundtrip_bottle(library_store, sample_bottle, tmp_path):
    library_store.upsert_bottle(sample_bottle)
    path = tmp_path / "rt.jsonl"
    io_jsonl.export_jsonl_bottles(library_store, path)
    library_store.bottles.clear()
    io_jsonl.import_jsonl_bottles(library_store, path)
    assert len(library_store.bottles) == 1


def test_export_creates_file(library_store, tmp_path):
    out = tmp_path / "new.jsonl"
    io_jsonl.export_jsonl_bottles(library_store, out)
    assert out.exists()


def test_import_tasting_count(library_store, sample_tasting, tmp_path):
    dest = tmp_path / "one.jsonl"
    dest.write_text(json.dumps(sample_tasting.to_dict()) + "\n", encoding="utf-8")
    assert io_jsonl.import_jsonl_tastings(library_store, dest) == 1


def test_export_utf8(library_store, tmp_path):
    b = Bottle.create("Café résumé")
    library_store.upsert_bottle(b)
    path = tmp_path / "u.jsonl"
    io_jsonl.export_jsonl_bottles(library_store, path)
    assert "Café" in path.read_text(encoding="utf-8")


def test_import_jsonl_bottles_upserts(library_store, sample_bottle, tmp_path):
    dest = tmp_path / "up.jsonl"
    d = sample_bottle.to_dict()
    d["title"] = "Original"
    dest.write_text(json.dumps(d) + "\n", encoding="utf-8")
    io_jsonl.import_jsonl_bottles(library_store, dest)
    d["title"] = "Updated"
    dest.write_text(json.dumps(d) + "\n", encoding="utf-8")
    io_jsonl.import_jsonl_bottles(library_store, dest)
    assert library_store.bottles[sample_bottle.id].title == "Updated"


def test_export_tastings_count(library_store, sample_tasting):
    library_store.tastings[sample_tasting.id] = sample_tasting
    assert len(library_store.tastings) == 1


def test_import_invalid_json_raises(library_store, tmp_path):
    dest = tmp_path / "bad.jsonl"
    dest.write_text("{broken\n", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        io_jsonl.import_jsonl_bottles(library_store, dest)


def test_export_error_readonly(tmp_path, library_store, monkeypatch):
    dest = tmp_path / "out.jsonl"

    def boom(*args, **kwargs):
        raise OSError("denied")

    monkeypatch.setattr(Path, "open", boom)
    with pytest.raises(ExportError):
        io_jsonl.export_jsonl_bottles(library_store, dest)
