"""Tests for corklog.wishlist."""

import pytest
from corklog.errors import ValidationError
from corklog.wishlist import Wishlist


def test_wishlist_create(sample_wishlist):
    assert sample_wishlist.name == "to-buy"
    assert sample_wishlist.id


def test_empty_name_fails():
    with pytest.raises(ValidationError):
        Wishlist(name="")


def test_slug_from_name():
    sh = Wishlist(name="open")
    assert sh.slug == "open"


def test_add_bottle():
    sh = Wishlist(name="favorites")
    assert sh.add_bottle("b1") is True
    assert sh.count() == 1


def test_add_bottle_duplicate():
    sh = Wishlist(name="favorites")
    sh.add_bottle("b1")
    assert sh.add_bottle("b1") is False


def test_remove_bottle():
    sh = Wishlist(name="favorites")
    sh.add_bottle("b1")
    assert sh.remove_bottle("b1") is True
    assert sh.count() == 0


def test_remove_missing():
    sh = Wishlist(name="favorites")
    assert sh.remove_bottle("nope") is False


def test_to_dict_roundtrip():
    sh = Wishlist(name="queue", description="next up")
    d = sh.to_dict()
    sh2 = Wishlist.from_dict(d)
    assert sh2.name == sh.name
    assert sh2.description == sh.description


def test_count():
    sh = Wishlist(name="x")
    sh.bottle_ids = ["a", "b", "c"]
    assert sh.count() == 3


def test_is_default_flag():
    sh = Wishlist(name="default-wishlist", is_default=True)
    assert sh.is_default is True


def test_is_public_flag():
    sh = Wishlist(name="public-list", is_public=True)
    assert sh.is_public is True


def test_sort_order():
    sh = Wishlist(name="ordered", sort_order=5)
    assert sh.sort_order == 5


def test_created_at_serialized():
    sh = Wishlist(name="dated")
    d = sh.to_dict()
    assert "created_at" in d


def test_from_dict_parses_created_at():
    sh = Wishlist(name="x")
    d = sh.to_dict()
    sh2 = Wishlist.from_dict(d)
    assert sh2.created_at is not None


def test_bottle_ids_list_copy_safe():
    sh = Wishlist(name="x")
    sh.add_bottle("b1")
    d = sh.to_dict()
    sh2 = Wishlist.from_dict(d)
    sh2.add_bottle("b2")
    assert sh.count() == 1


def test_description_default_empty():
    sh = Wishlist(name="minimal")
    assert sh.description == ""


def test_id_generated():
    sh = Wishlist(name="auto-id")
    assert len(sh.id) >= 8


def test_multiple_bottles_order():
    sh = Wishlist(name="x")
    for bid in ["c", "a", "b"]:
        sh.add_bottle(bid)
    assert sh.bottle_ids == ["c", "a", "b"]
