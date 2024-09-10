"""Tests for corklog.tasting."""

from datetime import date

import pytest

from corklog.errors import ValidationError
from corklog.tasting import Tasting, Session


def test_create():
    t = Tasting.create("b1", ml_start=0, ml_end=150, score=4.0)
    assert t.bottle_id == "b1"
    assert t.poured_ml() == 150


def test_poured_ml():
    assert Tasting.create("b", ml_start=50, ml_end=200).poured_ml() == 150


def test_poured_ml_zero():
    assert Tasting.create("b", ml_start=0, ml_end=0).poured_ml() == 0


def test_negative_rejected():
    with pytest.raises(ValidationError):
        Tasting(bottle_id="b", ml_start=-5)


def test_end_before_start_rejected():
    with pytest.raises(ValueError):
        Tasting(bottle_id="b", ml_start=200, ml_end=50)


def test_tasting_date():
    t = Tasting.create("b", started_at="2025-03-15T20:00:00")
    assert t.tasting_date == date(2025, 3, 15)


def test_score_optional():
    assert Tasting.create("b").score is None


def test_occasion_and_with_whom():
    t = Tasting.create("b", occasion="anniversary", with_whom="Sara")
    assert t.occasion == "anniversary" and t.with_whom == "Sara"


def test_is_blind():
    assert Tasting.create("b", occasion="blind flight").is_blind() is True
    assert Tasting.create("b", occasion="dinner").is_blind() is False


def test_to_from_dict_roundtrip():
    t = Tasting.create("b", ml_start=0, ml_end=120, score=4.5, occasion="dinner", notes="lovely")
    t2 = Tasting.from_dict(t.to_dict())
    assert t2.poured_ml() == 120 and t2.score == 4.5 and t2.notes == "lovely"


def test_id_generated():
    assert Tasting.create("b").id


def test_session_alias():
    assert Session is Tasting
