"""Tests for corklog.io_winesearcher (Wine-Searcher API wrapper)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from corklog.errors import ImportError as PTImportError
from corklog import io_winesearcher

LWIN = "1011266"

MARGAUX = {
    "wines": [
        {
            "name": "Château Margaux",
            "vintage": 2015,
            "region": "Bordeaux",
            "country": "France",
            "price": 650.0,
            "currency": "USD",
            "note": "First growth, profound.",
        }
    ]
}


def _resp(payload):
    m = MagicMock()
    m.read.return_value = json.dumps(payload).encode("utf-8")
    m.__enter__ = lambda s: s
    m.__exit__ = MagicMock(return_value=False)
    return m


def test_base_url():
    assert io_winesearcher.BASE.startswith("https://")


@patch("urllib.request.urlopen")
def test_fetch_by_lwin(mock_urlopen):
    mock_urlopen.return_value = _resp(MARGAUX)
    data = io_winesearcher.fetch_by_lwin(LWIN)
    assert data["wines"][0]["name"] == "Château Margaux"


def test_fetch_bad_lwin():
    with pytest.raises(PTImportError):
        io_winesearcher.fetch_by_lwin("not-a-lwin")


@patch("urllib.request.urlopen")
def test_fetch_network_error(mock_urlopen):
    mock_urlopen.side_effect = OSError("offline")
    with pytest.raises(PTImportError):
        io_winesearcher.fetch_by_lwin(LWIN)


@patch("urllib.request.urlopen")
def test_fetch_bad_json(mock_urlopen):
    m = MagicMock()
    m.read.return_value = b"not json"
    m.__enter__ = lambda s: s
    m.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = m
    with pytest.raises(PTImportError):
        io_winesearcher.fetch_by_lwin(LWIN)


@patch("urllib.request.urlopen")
def test_bottle_from_lwin(mock_urlopen):
    mock_urlopen.return_value = _resp(MARGAUX)
    b = io_winesearcher.bottle_from_lwin(LWIN)
    assert b.title == "Château Margaux"
    assert b.vintage == 2015
    assert b.price == 650.0
    assert b.country == "France"


@patch("urllib.request.urlopen")
def test_bottle_from_lwin_keeps_lwin(mock_urlopen):
    mock_urlopen.return_value = _resp(MARGAUX)
    assert io_winesearcher.bottle_from_lwin(LWIN).lwin == LWIN


@patch("urllib.request.urlopen")
def test_bottle_from_lwin_source(mock_urlopen):
    mock_urlopen.return_value = _resp(MARGAUX)
    assert io_winesearcher.bottle_from_lwin(LWIN).source == "winesearcher"


@patch("urllib.request.urlopen")
def test_bottle_from_lwin_region_metadata(mock_urlopen):
    mock_urlopen.return_value = _resp(MARGAUX)
    assert io_winesearcher.bottle_from_lwin(LWIN).metadata.get("region") == "Bordeaux"


@patch("urllib.request.urlopen")
def test_bottle_from_lwin_no_match(mock_urlopen):
    mock_urlopen.return_value = _resp({"wines": []})
    with pytest.raises(PTImportError):
        io_winesearcher.bottle_from_lwin(LWIN)


@patch("urllib.request.urlopen")
def test_bottle_from_lwin_unknown_name(mock_urlopen):
    mock_urlopen.return_value = _resp({"wines": [{"vintage": 2010}]})
    assert io_winesearcher.bottle_from_lwin(LWIN).title == "Unknown Wine"


@patch("urllib.request.urlopen")
def test_search(mock_urlopen):
    mock_urlopen.return_value = _resp({"results": [{"name": "A"}, {"name": "B"}]})
    assert len(io_winesearcher.search("margaux", limit=1)) == 1


@patch("urllib.request.urlopen")
def test_search_network_fail(mock_urlopen):
    mock_urlopen.side_effect = OSError("nope")
    assert io_winesearcher.search("x") == []


@patch("urllib.request.urlopen")
def test_enrich_bottle(mock_urlopen, storage_with_bottle, sample_bottle):
    sample_bottle.lwin = LWIN
    storage_with_bottle.upsert_bottle(sample_bottle)
    mock_urlopen.return_value = _resp(MARGAUX)
    enriched = io_winesearcher.enrich_bottle(storage_with_bottle, sample_bottle.id)
    assert enriched.price == 650.0


def test_enrich_no_lwin(empty_storage, sample_bottle):
    sample_bottle.lwin = None
    empty_storage.upsert_bottle(sample_bottle)
    with pytest.raises(PTImportError):
        io_winesearcher.enrich_bottle(empty_storage, sample_bottle.id)


@patch("urllib.request.urlopen")
def test_enrich_no_match_keeps_bottle(mock_urlopen, storage_with_bottle, sample_bottle):
    sample_bottle.lwin = LWIN
    storage_with_bottle.upsert_bottle(sample_bottle)
    mock_urlopen.return_value = _resp({"wines": []})
    assert io_winesearcher.enrich_bottle(storage_with_bottle, sample_bottle.id).id == sample_bottle.id


@patch("urllib.request.urlopen")
def test_bulk_enrich(mock_urlopen, storage_with_bottle, sample_bottle):
    sample_bottle.lwin = LWIN
    storage_with_bottle.upsert_bottle(sample_bottle)
    mock_urlopen.return_value = _resp(MARGAUX)
    assert io_winesearcher.bulk_enrich(storage_with_bottle, limit=5) >= 1


def test_format_search_hit():
    line = io_winesearcher.format_search_hit({"name": "Margaux", "vintage": 2015, "price": 650})
    assert "Margaux" in line and "650" in line


def test_format_search_hit_nv():
    assert "NV" in io_winesearcher.format_search_hit({"name": "Champagne"})
