"""Tests for corklog.lwin (LWIN identifier handling)."""

import pytest

from corklog import lwin as lwin_mod

L7 = "1011266"
L11 = "10112662015"


def test_validate_lwin7():
    assert lwin_mod.validate_lwin(L7) is True


def test_validate_lwin11():
    assert lwin_mod.validate_lwin(L11) is True


def test_validate_garbage():
    assert lwin_mod.validate_lwin("not-a-lwin") is False


def test_validate_empty():
    assert lwin_mod.validate_lwin("") is False
    assert lwin_mod.validate_lwin(None) is False


def test_validate_wrong_length():
    assert lwin_mod.validate_lwin("12345") is False  # 5 digits


def test_is_lwin():
    assert lwin_mod.is_lwin(L7) is True
    assert lwin_mod.is_lwin("123") is False


def test_normalize_strips_separators():
    assert lwin_mod.normalize_lwin("1011266") == "1011266"
    assert lwin_mod.normalize_lwin("1011 266") == "1011266"
    assert lwin_mod.normalize_lwin("1011-266") == "1011266"


def test_normalize_bad_raises():
    with pytest.raises(ValueError):
        lwin_mod.normalize_lwin("nope")


def test_normalize_helper_none():
    assert lwin_mod.normalize("garbage") is None


def test_normalize_helper_value():
    assert lwin_mod.normalize(L7) == L7


def test_parse():
    assert lwin_mod.parse("1011266") == L7


def test_base7():
    assert lwin_mod.base7(L11) == "1011266"


def test_base7_none():
    assert lwin_mod.base7("junk") is None


def test_vintage_part():
    assert lwin_mod.vintage_part(L11) == 2015


def test_vintage_part_none_for_lwin7():
    assert lwin_mod.vintage_part(L7) is None


def test_lwin_kind():
    assert lwin_mod.lwin_kind(L7) == "lwin7"
    assert lwin_mod.lwin_kind(L11) == "lwin11"
    assert lwin_mod.lwin_kind("nope") == "unknown"


def test_format_display_lwin11():
    assert "2015" in lwin_mod.format_display(L11)


def test_format_display_lwin7():
    assert lwin_mod.format_display(L7) == "LWIN 1011266"


def test_format_display_unknown():
    assert lwin_mod.format_display("weird") == "weird"


def test_guess_lwin():
    assert lwin_mod.guess_lwin("see 1011266 on the label") == L7


def test_guess_lwin_none():
    assert lwin_mod.guess_lwin("no id here") is None


def test_clean_id_list():
    out = lwin_mod.clean_id_list("1011266, junk, 10112662015")
    assert out == ["1011266", "10112662015"]


def test_batch_validate():
    d = lwin_mod.batch_validate([L7, "nope"])
    assert d[L7] is True and d["nope"] is False


def test_compare_lwin_same_wine():
    assert lwin_mod.compare_lwin(L7, L11) is True  # both base7 1011266


def test_compare_lwin_unequal():
    assert lwin_mod.compare_lwin(L7, "1234567") is False


def test_compare_lwin_invalid():
    assert lwin_mod.compare_lwin(L7, "junk") is False


def test_explain_valid():
    assert "valid" in lwin_mod.explain(L7)


def test_explain_invalid():
    assert lwin_mod.explain("##") == "invalid lwin"


def test_explain_empty():
    assert lwin_mod.explain("") == "empty id"


def test_aliases():
    assert lwin_mod.is_valid(L7) is True
    assert lwin_mod.validate(L7) is True
    assert lwin_mod.format_lwin(L7) == "LWIN 1011266"
