"""Tests for corklog.io_cellartracker (CellarTracker CSV export)."""

import pytest

from corklog.errors import ImportError as PTImportError
from corklog.bottle import CellarStatus
from corklog import io_cellartracker

CT_CSV = """\
iWine,Wine,Vintage,Producer,Varietal,Country,Region,Quantity,Price,BeginConsume,EndConsume
1011266,Château Margaux,2015,Château Margaux,Cabernet Sauvignon,France,Bordeaux,3,650,2030,2055
2033444,Penfolds Grange,2016,Penfolds,Shiraz,Australia,South Australia,1,900,2026,2046
"""


def _w(tmp_path, text, name="ct.csv"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_import_count(library_store, tmp_path):
    assert io_cellartracker.import_cellartracker(library_store, _w(tmp_path, CT_CSV)) == 2


def test_import_missing(library_store, tmp_path):
    with pytest.raises(PTImportError):
        io_cellartracker.import_cellartracker(library_store, tmp_path / "nope.csv")


def test_status_cellared(library_store, tmp_path):
    io_cellartracker.import_cellartracker(library_store, _w(tmp_path, CT_CSV))
    assert all(b.status == CellarStatus.CELLARED for b in library_store.bottles.values())


def test_vintage_and_varietal(library_store, tmp_path):
    io_cellartracker.import_cellartracker(library_store, _w(tmp_path, CT_CSV))
    margaux = next(b for b in library_store.bottles.values() if b.title == "Château Margaux")
    assert margaux.vintage == 2015
    assert margaux.varietal == "Cabernet Sauvignon"
    assert margaux.country == "France"


def test_price_and_window(library_store, tmp_path):
    io_cellartracker.import_cellartracker(library_store, _w(tmp_path, CT_CSV))
    margaux = next(b for b in library_store.bottles.values() if b.title == "Château Margaux")
    assert margaux.price == 650.0
    assert margaux.drink_from == 2030 and margaux.drink_to == 2055


def test_iwine_and_quantity_metadata(library_store, tmp_path):
    io_cellartracker.import_cellartracker(library_store, _w(tmp_path, CT_CSV))
    margaux = next(b for b in library_store.bottles.values() if b.title == "Château Margaux")
    assert margaux.metadata.get("iwine") == "1011266"
    assert margaux.metadata.get("quantity") == "3"


def test_producer_created(library_store, tmp_path):
    io_cellartracker.import_cellartracker(library_store, _w(tmp_path, CT_CSV))
    names = {p.name for p in library_store.producers.values()}
    assert "Penfolds" in names


def test_producer_reused(library_store, tmp_path):
    csv = ("iWine,Wine,Vintage,Producer\n"
           "1,A 2015,2015,Penfolds\n2,B 2016,2016,Penfolds\n")
    io_cellartracker.import_cellartracker(library_store, _w(tmp_path, csv))
    assert len(library_store.producers) == 1


def test_source(library_store, tmp_path):
    io_cellartracker.import_cellartracker(library_store, _w(tmp_path, CT_CSV))
    assert all(b.source == "cellartracker" for b in library_store.bottles.values())


def test_blank_wine_skipped(library_store, tmp_path):
    csv = "iWine,Wine,Vintage\n9,,2015\n"
    assert io_cellartracker.import_cellartracker(library_store, _w(tmp_path, csv)) == 0


def test_price_with_dollar(library_store, tmp_path):
    csv = "Wine,Price\nCheap Red,$12.50\n"
    io_cellartracker.import_cellartracker(library_store, _w(tmp_path, csv))
    assert next(iter(library_store.bottles.values())).price == 12.5


def test_preview(tmp_path):
    lines = io_cellartracker.preview(_w(tmp_path, CT_CSV), limit=1)
    assert lines and "Margaux" in lines[0]


def test_preview_missing(tmp_path):
    assert io_cellartracker.preview(tmp_path / "no.csv") == []


def test_cellared_count(library_store, tmp_path):
    io_cellartracker.import_cellartracker(library_store, _w(tmp_path, CT_CSV))
    assert io_cellartracker.cellared_count(library_store) == 2


def test_export_roundtrip(library_store, tmp_path):
    io_cellartracker.import_cellartracker(library_store, _w(tmp_path, CT_CSV))
    dest = tmp_path / "out.csv"
    assert io_cellartracker.export_cellartracker_csv(library_store, dest) == 2
    assert "Margaux" in dest.read_text(encoding="utf-8")


def test_conftest_fixture(library_store, cellartracker_csv_tmp):
    assert io_cellartracker.import_cellartracker(library_store, cellartracker_csv_tmp) == 2
