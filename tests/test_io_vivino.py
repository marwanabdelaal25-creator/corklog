"""Tests for corklog.io_vivino (Vivino CSV export)."""

import pytest

from corklog.errors import ImportError as PTImportError
from corklog.bottle import CellarStatus
from corklog import io_vivino

VIVINO_CSV = """\
Winery,Wine name,Vintage,Region,Country,Your rating,Scan date
Cloudy Bay,Sauvignon Blanc,2022,Marlborough,New Zealand,4.5,2024-02-01
Tignanello,Tignanello,2019,Tuscany,Italy,4.0,2024-02-08
"""

WISHLIST_CSV = """\
Winery,Wine name,Vintage,Region,Country
Sassicaia,Sassicaia,2020,Tuscany,Italy
"""


def _w(tmp_path, text, name="vivino.csv"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_import_count(library_store, tmp_path):
    assert io_vivino.import_vivino(library_store, _w(tmp_path, VIVINO_CSV)) == 2


def test_import_missing(library_store, tmp_path):
    with pytest.raises(PTImportError):
        io_vivino.import_vivino(library_store, tmp_path / "nope.csv")


def test_rated_marks_drunk(library_store, tmp_path):
    io_vivino.import_vivino(library_store, _w(tmp_path, VIVINO_CSV))
    cb = next(b for b in library_store.bottles.values() if b.title == "Sauvignon Blanc")
    assert cb.status == CellarStatus.DRUNK
    assert cb.finished_at == "2024-02-01"


def test_unrated_marks_want(library_store, tmp_path):
    io_vivino.import_vivino(library_store, _w(tmp_path, WISHLIST_CSV))
    assert next(iter(library_store.bottles.values())).status == CellarStatus.WANT


def test_rating_imported(library_store, tmp_path):
    io_vivino.import_vivino(library_store, _w(tmp_path, VIVINO_CSV))
    cb = next(b for b in library_store.bottles.values() if b.title == "Sauvignon Blanc")
    assert cb.rating_value == 4.5


def test_vintage_and_country(library_store, tmp_path):
    io_vivino.import_vivino(library_store, _w(tmp_path, VIVINO_CSV))
    cb = next(b for b in library_store.bottles.values() if b.title == "Sauvignon Blanc")
    assert cb.vintage == 2022 and cb.country == "New Zealand"


def test_producer_from_winery(library_store, tmp_path):
    io_vivino.import_vivino(library_store, _w(tmp_path, VIVINO_CSV))
    names = {p.name for p in library_store.producers.values()}
    assert "Cloudy Bay" in names


def test_producer_reused(library_store, tmp_path):
    csv = ("Winery,Wine name,Your rating,Scan date\n"
           "Penfolds,Bin 28,4,2024-01-01\nPenfolds,Bin 389,5,2024-01-02\n")
    io_vivino.import_vivino(library_store, _w(tmp_path, csv))
    assert len(library_store.producers) == 1


def test_source(library_store, tmp_path):
    io_vivino.import_vivino(library_store, _w(tmp_path, VIVINO_CSV))
    assert all(b.source == "vivino" for b in library_store.bottles.values())


def test_region_metadata(library_store, tmp_path):
    io_vivino.import_vivino(library_store, _w(tmp_path, VIVINO_CSV))
    cb = next(b for b in library_store.bottles.values() if b.title == "Sauvignon Blanc")
    assert cb.metadata.get("region") == "Marlborough"


def test_blank_name_skipped(library_store, tmp_path):
    csv = "Winery,Wine name\nNobody,\n"
    assert io_vivino.import_vivino(library_store, _w(tmp_path, csv)) == 0


def test_bad_rating_ignored(library_store, tmp_path):
    csv = "Winery,Wine name,Your rating\nX,Y,notnum\n"
    io_vivino.import_vivino(library_store, _w(tmp_path, csv))
    assert next(iter(library_store.bottles.values())).rating is None


def test_preview(tmp_path):
    lines = io_vivino.preview(_w(tmp_path, VIVINO_CSV), limit=1)
    assert lines and "Cloudy Bay" in lines[0]


def test_preview_missing(tmp_path):
    assert io_vivino.preview(tmp_path / "no.csv") == []


def test_scanned_helper(library_store, tmp_path):
    io_vivino.import_vivino(library_store, _w(tmp_path, VIVINO_CSV))
    assert len(io_vivino.scanned(library_store)) == 2


def test_history_summary(library_store, tmp_path):
    io_vivino.import_vivino(library_store, _w(tmp_path, VIVINO_CSV))
    assert "Vivino scans" in io_vivino.history_summary(library_store)


def test_history_summary_empty(library_store):
    assert "No Vivino" in io_vivino.history_summary(library_store)


def test_conftest_fixture(library_store, vivino_csv):
    assert io_vivino.import_vivino(library_store, vivino_csv) == 2
