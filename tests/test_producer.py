"""Tests for corklog.producer."""

import pytest
from corklog.producer import Producer
from corklog.errors import ValidationError


def test_create_producer(sample_producer):
    assert sample_producer.name == "Domaine de la Romanée-Conti"
    assert sample_producer.id


def test_create_empty_name():
    with pytest.raises(ValidationError):
        Producer.create("  ")


def test_to_dict_roundtrip(sample_producer):
    d = sample_producer.to_dict()
    a2 = Producer.from_dict(d)
    assert a2.name == sample_producer.name


def test_display_name():
    a = Producer.create("Jane Doe")
    assert a.display_name() == "Jane Doe"


def test_add_bottle():
    a = Producer.create("A")
    a.add_bottle("b1")
    assert "b1" in a.bottle_ids


def test_add_bottle_no_dup():
    a = Producer.create("A")
    a.add_bottle("b1")
    a.add_bottle("b1")
    assert a.bottle_ids.count("b1") == 1


def test_remove_bottle():
    a = Producer.create("A")
    a.add_bottle("b1")
    a.remove_bottle("b1")
    assert "b1" not in a.bottle_ids


def test_remove_bottle_missing():
    a = Producer.create("A")
    a.remove_bottle("nope")  # shouldn't raise


def test_merge_aliases():
    a = Producer.create("A", aliases=["pen name"])
    a.merge_aliases(["Pen Name", "other"])
    assert len(a.aliases) >= 2


def test_merge_aliases_skips_empty():
    a = Producer.create("A")
    a.merge_aliases(["", "  "])
    assert a.aliases == []


def test_email_validated():
    a = Producer.create("A", email="x@y.z")
    assert a.email == "x@y.z"


def test_email_invalid():
    with pytest.raises(ValidationError):
        Producer.create("A", email="bad")


def test_positional_init():
    a = Producer(name="Direct")
    assert a.name == "Direct"


def test_aliases_default_empty():
    a = Producer.create("A")
    assert a.aliases == []


def test_bottle_ids_independent():
    a1 = Producer.create("A")
    a2 = Producer.from_dict(a1.to_dict())
    a2.bottle_ids.append("x")
    assert "x" not in a1.bottle_ids


def test_bio_preserved():
    a = Producer.create("A", bio="Wrote many bottles.")
    assert "many" in a.to_dict()["bio"]


def test_website_field():
    a = Producer.create("A", website="https://example.com")
    assert a.website.startswith("https")


def test_birth_death_years():
    a = Producer.create("A", birth_year=1920, death_year=2000)
    assert a.death_year - a.birth_year == 80


def test_from_dict_minimal():
    a = Producer.from_dict({"id": "1", "name": "N"})
    assert a.bio == ""

from corklog.errors import ConflictError
from corklog.producer import Producer, ProducerManager


def test_producer_manager_create_find(storage_with_bottle):
    am = ProducerManager(storage_with_bottle)
    au = am.create("Brand New")
    assert am.find_by_name("Brand New") is not None


def test_producer_manager_duplicate(storage_with_bottle):
    am = ProducerManager(storage_with_bottle)
    am.create("Dup Producer")
    with pytest.raises(ConflictError):
        am.create("Dup Producer")


def test_producer_manager_attach(storage_with_bottle, sample_bottle, sample_producer):
    storage_with_bottle.upsert_producer(sample_producer)
    storage_with_bottle.upsert_bottle(sample_bottle)
    am = ProducerManager(storage_with_bottle)
    am.attach_bottle(sample_producer.id, sample_bottle.id)
    assert sample_bottle.id in am.bottles_for(sample_producer.id)


def test_producer_matches_alias():
    au = Producer.create("Name", aliases=["Pen Name"])
    assert au.matches("pen") is True
