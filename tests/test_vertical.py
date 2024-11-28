"""Tests for corklog.vertical."""

import pytest
from corklog.errors import ValidationError
from corklog.vertical import Vertical


def test_vertical_create():
    s = Vertical(title="The Expanse")
    assert s.title == "The Expanse"


def test_empty_title_fails():
    with pytest.raises(ValidationError):
        Vertical(title="")


def test_add_volume():
    s = Vertical(title="X")
    s.add_volume("b1")
    assert "b1" in s.bottle_ids


def test_add_volume_no_dup():
    s = Vertical(title="X")
    s.add_volume("b1")
    s.add_volume("b1")
    assert s.bottle_ids.count("b1") == 1


def test_completion_pct_empty():
    s = Vertical(title="X")
    assert s.completion_pct(set()) == 0.0


def test_completion_pct_partial():
    s = Vertical(title="X", bottle_ids=["b1", "b2", "b3", "b4"])
    pct = s.completion_pct({"b1", "b2"})
    assert pct == 50.0


def test_completion_pct_full():
    s = Vertical(title="X", bottle_ids=["b1"])
    assert s.completion_pct({"b1"}) == 100.0


def test_to_dict_roundtrip():
    s = Vertical(title="S", producer_id="a1", total_planned=7)
    s2 = Vertical.from_dict(s.to_dict())
    assert s2.total_planned == 7


def test_producer_id_optional():
    s = Vertical(title="Standalone")
    assert s.producer_id is None


def test_description_field():
    s = Vertical(title="D", description="Long arc")
    assert "arc" in s.description


def test_bottle_ids_default_empty():
    s = Vertical(title="New")
    assert s.bottle_ids == []


def test_total_planned_optional():
    s = Vertical(title="Open", total_planned=None)
    assert s.total_planned is None


def test_id_generated():
    assert len(Vertical(title="T").id) >= 8


def test_from_dict_preserves_bottle_ids():
    d = {"title": "T", "bottle_ids": ["a", "b"]}
    s = Vertical.from_dict(d)
    assert s.bottle_ids == ["a", "b"]


def test_completion_rounding():
    s = Vertical(title="X", bottle_ids=["1", "2", "3"])
    pct = s.completion_pct({"1"})
    assert pct == round(100.0 / 3, 1)


def test_title_required_in_from_dict():
    s = Vertical.from_dict({"title": "OK"})
    assert s.title == "OK"


def test_multiple_volumes_order():
    s = Vertical(title="X")
    for bid in ["v3", "v1", "v2"]:
        s.add_volume(bid)
    assert s.bottle_ids == ["v3", "v1", "v2"]


def test_completion_ignores_unknown_reads():
    s = Vertical(title="X", bottle_ids=["b1"])
    assert s.completion_pct({"b1", "other"}) == 100.0


def test_description_default_empty():
    assert Vertical(title="Z").description == ""

import pytest
from corklog.bottle import CellarStatus
from corklog.errors import NotFoundError
from corklog.vertical import VerticalRegistry


def test_remove_volume():
    s = Vertical(title="S", bottle_ids=["a", "b"])
    s.remove_volume("a")
    assert "a" not in s.bottle_ids


def test_next_undrunk():
    s = Vertical(title="S", bottle_ids=["a", "b"])
    assert s.next_undrunk(set()) == "a"
    assert s.next_undrunk({"a"}) == "b"


def test_vertical_registry_create_attach(storage_with_bottle, sample_bottle):
    sr = VerticalRegistry(storage_with_bottle)
    s = sr.create("The Expanse")
    sr.attach_bottle(s.id, sample_bottle.id, index=1.0)
    assert sample_bottle.id in sr.get(s.id).bottle_ids


def test_vertical_registry_find_by_title(storage_with_bottle):
    sr = VerticalRegistry(storage_with_bottle)
    sr.create("Mistborn")
    assert sr.find_by_title("mist")


def test_vertical_registry_progress_report(storage_with_bottle, sample_bottle):
    sr = VerticalRegistry(storage_with_bottle)
    s = sr.create("Report Vertical")
    sr.attach_bottle(s.id, sample_bottle.id)
    assert "Report" in sr.progress_report()


def test_vertical_registry_get_missing(empty_storage):
    with pytest.raises(NotFoundError):
        VerticalRegistry(empty_storage).get("nope")


def test_progress_report_lines_read(storage_with_bottle, sample_read_bottle):
    sr = VerticalRegistry(storage_with_bottle)
    s = sr.create("Done Vertical")
    sr.attach_bottle(s.id, sample_read_bottle.id)
    lines = sr.progress_report_lines()
    assert any("100" in ln or "Done" in ln for ln in lines)
