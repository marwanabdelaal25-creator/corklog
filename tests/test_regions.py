"""Tests for corklog.regions."""

import pytest
from corklog.errors import ValidationError
from corklog.regions import Region


def test_region_create():
    p = Region(name="Tor Bottles")
    assert p.name == "Tor Bottles"


def test_empty_name_fails():
    with pytest.raises(ValidationError):
        Region(name="")


def test_to_dict_roundtrip():
    p = Region(name="Ace", country="US", website="https://ace.com")
    d = p.to_dict()
    p2 = Region.from_dict(d)
    assert p2.name == p.name


def test_matches_name():
    p = Region(name="Penguin Random House")
    assert p.matches("penguin") is True


def test_matches_imprint():
    p = Region(name="Big Five", imprint="Vintage")
    assert p.matches("vintage") is True


def test_no_match():
    p = Region(name="Small Press")
    assert p.matches("xyz") is False


def test_id_generated():
    p = Region(name="Auto")
    assert p.id


def test_country_default_empty():
    p = Region(name="X")
    assert p.country == ""


def test_imprint_field():
    p = Region(name="Parent", imprint="Child")
    assert p.imprint == "Child"


def test_from_dict_partial():
    p = Region.from_dict({"name": "Only Name"})
    assert p.name == "Only Name"


def test_website_stored():
    p = Region(name="W", website="http://w.example")
    assert "example" in p.website


def test_matches_case_insensitive():
    p = Region(name="Orbit")
    assert p.matches("ORBIT") is True


def test_to_dict_keys():
    keys = set(Region(name="K").to_dict().keys())
    assert {"name", "id", "country", "website", "imprint"} <= keys


def test_name_stripped_on_init():
    p = Region(name="  Trimmed  ")
    assert p.name == "Trimmed"


def test_from_dict_id_preserved():
    p = Region.from_dict({"id": "pub-99", "name": "N"})
    assert p.id == "pub-99"


def test_matches_empty_query():
    p = Region(name="X")
    assert p.matches("") is True


def test_multiple_regions_unique_ids():
    a = Region(name="A")
    b = Region(name="B")
    assert a.id != b.id


def test_imprint_default_empty():
    assert Region(name="Y").imprint == ""

import pytest
from corklog.errors import NotFoundError
from corklog.regions import RegionIndex


def test_region_index_assign(storage_with_bottle, sample_bottle):
    pi = RegionIndex(storage_with_bottle)
    pi.assign_bottle(sample_bottle.id, "Tor Bottles")
    pub = pi.find_or_create("Tor Bottles")
    assert len(pi.bottles_for(pub.id)) == 1


def test_region_index_search(storage_with_bottle, sample_bottle):
    pi = RegionIndex(storage_with_bottle)
    pi.assign_bottle(sample_bottle.id, "Ace")
    hits = pi.search("ace")
    assert len(hits) >= 1


def test_region_index_export_csv(storage_with_bottle, sample_bottle):
    pi = RegionIndex(storage_with_bottle)
    pi.assign_bottle(sample_bottle.id, "Orbit")
    lines = pi.export_csv_lines()
    assert lines[0].startswith("name,")


def test_region_index_summary(storage_with_bottle, sample_bottle):
    pi = RegionIndex(storage_with_bottle)
    pi.assign_bottle(sample_bottle.id, "Del Rey")
    assert "Del Rey" in pi.summary()


def test_region_index_get_missing(empty_storage):
    with pytest.raises(NotFoundError):
        RegionIndex(empty_storage).get("nope")


def test_region_index_list_sorted(storage_with_bottle, sample_bottle):
    pi = RegionIndex(storage_with_bottle)
    pi.find_or_create("Zebra")
    pi.find_or_create("Alpha")
    names = [p.name for p in pi.list_all()]
    assert names == sorted(names, key=str.lower)


def test_region_invalid_website():
    with pytest.raises(Exception):
        from corklog.errors import ValidationError
        Region(name="Bad", website="not-a-url")
