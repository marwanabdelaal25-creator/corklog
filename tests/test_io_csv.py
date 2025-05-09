"""Tests for corklog.io_csv."""

import pytest

from corklog.bottle import CellarStatus
from corklog import io_csv


def test_csv_fields_count():
    assert len(io_csv.CSV_FIELDS) == 10


def test_import_count(library_store, mini_csv):
    assert io_csv.import_csv(library_store, mini_csv) == 2


def test_import_missing(library_store, tmp_path):
    from corklog.errors import ImportError as PTImportError

    with pytest.raises(PTImportError):
        io_csv.import_csv(library_store, tmp_path / "nope.csv")


def test_import_status_preserved(library_store, mini_csv):
    io_csv.import_csv(library_store, mini_csv)
    margaux = next(b for b in library_store.bottles.values() if "Margaux" in b.title)
    assert margaux.status == CellarStatus.CELLARED


def test_import_vintage_and_price(library_store, mini_csv):
    io_csv.import_csv(library_store, mini_csv)
    margaux = next(b for b in library_store.bottles.values() if "Margaux" in b.title)
    assert margaux.vintage == 2015 and margaux.price == 650.0


def test_import_varietal(library_store, mini_csv):
    io_csv.import_csv(library_store, mini_csv)
    cb = next(b for b in library_store.bottles.values() if "Cloudy Bay" in b.title)
    assert cb.varietal == "Sauvignon Blanc"


def test_import_rating(library_store, mini_csv):
    io_csv.import_csv(library_store, mini_csv)
    cb = next(b for b in library_store.bottles.values() if "Cloudy Bay" in b.title)
    assert cb.rating_value == 4.0


def test_import_creates_producer(library_store, mini_csv):
    io_csv.import_csv(library_store, mini_csv)
    names = {p.name for p in library_store.producers.values()}
    assert "Cloudy Bay" in names


def test_import_runtime_numeric(library_store, tmp_path):
    src = tmp_path / "p.csv"
    src.write_text(
        "title,producer,lwin,vintage,region,varietal,price,status,rating,tags\n"
        "Brunello,Biondi-Santi,,2016,Tuscany,Sangiovese,120,cellared,,\n",
        encoding="utf-8",
    )
    io_csv.import_csv(library_store, src)
    b = next(iter(library_store.bottles.values()))
    assert b.vintage == 2016 and b.price == 120.0


def test_import_blank_title_skipped(library_store, tmp_path):
    src = tmp_path / "b.csv"
    src.write_text("title,producer\n,Nobody\n", encoding="utf-8")
    assert io_csv.import_csv(library_store, src) == 0


def test_import_utf8_sig(library_store, tmp_path):
    src = tmp_path / "sig.csv"
    src.write_bytes("\ufefftitle,vintage\nSigned,2020\n".encode("utf-8"))
    assert io_csv.import_csv(library_store, src) == 1


def test_export_count(library_store, mini_csv, tmp_path):
    io_csv.import_csv(library_store, mini_csv)
    dest = tmp_path / "out.csv"
    assert io_csv.export_csv(library_store, dest) == 2


def test_export_includes_producer(library_store, mini_csv, tmp_path):
    io_csv.import_csv(library_store, mini_csv)
    dest = tmp_path / "out.csv"
    io_csv.export_csv(library_store, dest)
    assert "Cloudy Bay" in dest.read_text(encoding="utf-8")


def test_export_empty(library_store, tmp_path):
    assert io_csv.export_csv(library_store, tmp_path / "e.csv") == 0


def test_validate_headers_ok(mini_csv):
    assert io_csv.validate_csv_headers(mini_csv) == []


def test_validate_headers_missing(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("producer,vintage\nX,2020\n", encoding="utf-8")
    assert "title" in io_csv.validate_csv_headers(p)


def test_validate_headers_no_file(tmp_path):
    assert io_csv.validate_csv_headers(tmp_path / "none.csv") == io_csv.CSV_FIELDS


def test_parse_row():
    row = io_csv.parse_row("Margaux,Château Margaux,1011266")
    assert row["title"] == "Margaux"


def test_sample_rows(mini_csv):
    rows = io_csv.sample_rows(mini_csv, n=1)
    assert len(rows) == 1


def test_sample_rows_no_file(tmp_path):
    assert io_csv.sample_rows(tmp_path / "none.csv") == []


def test_import_update_mode(library_store, tmp_path):
    src = tmp_path / "u.csv"
    src.write_text("title,lwin,status\nFirst,1011266,cellared\n", encoding="utf-8")
    io_csv.import_csv(library_store, src)
    src.write_text("title,lwin,status\nFirst Renamed,1011266,drunk\n", encoding="utf-8")
    io_csv.import_csv(library_store, src, update=True)
    bottles = [b for b in library_store.bottles.values() if b.lwin == "1011266"]
    assert len(bottles) == 1 and bottles[0].title == "First Renamed"
