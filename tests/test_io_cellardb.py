"""Tests for corklog.io_cellardb (sqlite cellar import)."""

import json
import sqlite3

import pytest

from corklog.errors import ImportError as PTImportError
from corklog import io_cellardb


def _make_cellar(tmp_path, with_extras=True):
    lib = tmp_path / "cellar"
    lib.mkdir()
    db = lib / "cellar.db"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE bottles (id INTEGER PRIMARY KEY, wine TEXT, vintage TEXT, lwin TEXT, varietal TEXT, country TEXT, price REAL)")
    conn.execute("CREATE TABLE producers (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("CREATE TABLE bottles_producers_link (bottle INTEGER, producer INTEGER)")
    conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, bottle INTEGER, text TEXT)")
    conn.execute("INSERT INTO bottles VALUES (1, 'Château Margaux', '2015', '1011266', 'Cabernet Sauvignon', 'France', 650.0)")
    conn.execute("INSERT INTO producers VALUES (1, 'Château Margaux')")
    conn.execute("INSERT INTO bottles_producers_link VALUES (1, 1)")
    if with_extras:
        conn.execute("INSERT INTO notes VALUES (1, 1, 'Profound and tannic')")
    conn.commit()
    conn.close()
    return lib


def test_missing_db(tmp_path):
    with pytest.raises(PTImportError):
        io_cellardb._read_db(tmp_path / "empty")


def test_import_count(library_store, tmp_path):
    n = io_cellardb.import_cellardb(library_store, _make_cellar(tmp_path))
    assert n == 1
    assert next(iter(library_store.bottles.values())).title == "Château Margaux"


def test_import_producer(library_store, tmp_path):
    io_cellardb.import_cellardb(library_store, _make_cellar(tmp_path))
    assert len(library_store.producers) == 1


def test_import_note_to_description(library_store, tmp_path):
    io_cellardb.import_cellardb(library_store, _make_cellar(tmp_path))
    assert "Profound" in next(iter(library_store.bottles.values())).description


def test_import_vintage_and_price(library_store, tmp_path):
    io_cellardb.import_cellardb(library_store, _make_cellar(tmp_path))
    b = next(iter(library_store.bottles.values()))
    assert b.vintage == 2015 and b.price == 650.0


def test_import_lwin(library_store, tmp_path):
    io_cellardb.import_cellardb(library_store, _make_cellar(tmp_path))
    assert next(iter(library_store.bottles.values())).lwin == "1011266"


def test_import_invalid_lwin_dropped(library_store, tmp_path):
    lib = tmp_path / "bad"
    lib.mkdir()
    conn = sqlite3.connect(str(lib / "cellar.db"))
    conn.execute("CREATE TABLE bottles (id INTEGER PRIMARY KEY, wine TEXT, vintage TEXT, lwin TEXT, varietal TEXT, country TEXT, price REAL)")
    conn.execute("CREATE TABLE producers (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("CREATE TABLE bottles_producers_link (bottle INTEGER, producer INTEGER)")
    conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, bottle INTEGER, text TEXT)")
    conn.execute("INSERT INTO bottles VALUES (1, 'Mystery', NULL, 'not-a-lwin', NULL, NULL, NULL)")
    conn.commit()
    conn.close()
    io_cellardb.import_cellardb(library_store, lib)
    assert next(iter(library_store.bottles.values())).lwin is None


def test_import_source(library_store, tmp_path):
    io_cellardb.import_cellardb(library_store, _make_cellar(tmp_path))
    assert next(iter(library_store.bottles.values())).source == "cellardb"


def test_import_reuses_producer(library_store, tmp_path):
    lib = _make_cellar(tmp_path)
    io_cellardb.import_cellardb(library_store, lib)
    io_cellardb.import_cellardb(library_store, lib)
    assert len(library_store.producers) == 1


def test_import_unknown_wine(library_store, tmp_path):
    lib = tmp_path / "u"
    lib.mkdir()
    conn = sqlite3.connect(str(lib / "cellar.db"))
    conn.execute("CREATE TABLE bottles (id INTEGER PRIMARY KEY, wine TEXT, vintage TEXT, lwin TEXT, varietal TEXT, country TEXT, price REAL)")
    conn.execute("CREATE TABLE producers (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("CREATE TABLE bottles_producers_link (bottle INTEGER, producer INTEGER)")
    conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, bottle INTEGER, text TEXT)")
    conn.execute("INSERT INTO bottles VALUES (1, NULL, NULL, NULL, NULL, NULL, NULL)")
    conn.commit()
    conn.close()
    io_cellardb.import_cellardb(library_store, lib)
    assert next(iter(library_store.bottles.values())).title == "Unknown Wine"


def test_producer_link(library_store, tmp_path):
    io_cellardb.import_cellardb(library_store, _make_cellar(tmp_path))
    assert len(next(iter(library_store.bottles.values())).producer_ids) == 1


def test_list_wines(tmp_path):
    lib = _make_cellar(tmp_path)
    assert "Château Margaux" in io_cellardb.list_cellardb_wines(lib)


def test_export_json(library_store, sample_bottle):
    library_store.upsert_bottle(sample_bottle)
    data = json.loads(io_cellardb.export_cellardb_json(library_store))
    assert data[0]["wine"] == sample_bottle.title


def test_stats(tmp_path):
    lib = _make_cellar(tmp_path)
    s = io_cellardb.cellardb_stats(lib)
    assert s["bottles"] == 1 and s["producers"] == 1
