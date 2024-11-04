"""Tests for corklog.storage."""

import json

import pytest
from corklog.bottle import Bottle, CellarStatus
from corklog.producer import Producer
from corklog.errors import NotFoundError, StorageError
from corklog.tasting import Tasting
from corklog.wishlist import Wishlist
from corklog.storage import (
    JsonStorage,
    LibraryStore,
    SCHEMA_VERSION,
    open_storage,
    default_storage_path,
    _EMPTY,
)
from corklog.tag import Tag
from corklog.rating import Rating


def test_schema_version_constant():
    assert SCHEMA_VERSION == 2


def test_empty_structure_keys():
    assert "bottles" in _EMPTY
    assert "tastings" in _EMPTY


def test_json_storage_load_missing_file(json_storage):
    assert json_storage.list_bottles() == []


def test_json_storage_save_and_reload(tmp_path):
    path = tmp_path / "lib.json"
    st = JsonStorage(path)
    st.load()
    b = Bottle.create("Saved Bottle")
    st.upsert_bottle(b)
    st.save()
    st2 = JsonStorage(path)
    st2.load()
    assert len(st2.list_bottles()) == 1


def test_upsert_bottle_updates(json_storage, sample_bottle):
    json_storage.upsert_bottle(sample_bottle)
    sample_bottle.title = "Renamed"
    json_storage.upsert_bottle(sample_bottle)
    assert json_storage.get_bottle(sample_bottle.id).title == "Renamed"


def test_get_bottle_not_found(json_storage):
    with pytest.raises(NotFoundError):
        json_storage.get_bottle("missing")


def test_delete_bottle(json_storage, sample_bottle):
    json_storage.upsert_bottle(sample_bottle)
    json_storage.delete_bottle(sample_bottle.id)
    with pytest.raises(NotFoundError):
        json_storage.get_bottle(sample_bottle.id)


def test_delete_missing_raises(json_storage):
    with pytest.raises(NotFoundError):
        json_storage.delete_bottle("nope")


def test_list_producers(json_storage, sample_producer):
    json_storage.upsert_producer(sample_producer)
    assert len(json_storage.list_producers()) == 1


def test_upsert_wishlist(json_storage):
    sh = Wishlist(name="queue")
    json_storage.upsert_wishlist(sh)
    assert len(json_storage.list_wishlists()) == 1


def test_add_tasting(json_storage, sample_tasting):
    json_storage.add_tasting(sample_tasting)
    assert len(json_storage.list_tastings()) == 1


def test_list_tastings_filter(json_storage, sample_tasting):
    json_storage.add_tasting(sample_tasting)
    assert len(json_storage.list_tastings(bottle_id=sample_tasting.bottle_id)) == 1
    assert json_storage.list_tastings(bottle_id="other") == []


def test_tags_roundtrip(json_storage, sample_tag):
    json_storage.upsert_tag(sample_tag)
    tags = json_storage.list_tags()
    assert tags[0].slug == sample_tag.slug


def test_ratings_filter(json_storage, sample_rating):
    json_storage.add_rating(sample_rating)
    assert len(json_storage.list_ratings(bottle_id=sample_rating.bottle_id)) == 1


def test_raw_get_set(json_storage):
    json_storage.raw_set("custom", [1, 2])
    assert json_storage.raw_get("custom") == [1, 2]


def test_snapshot_is_copy(json_storage, sample_bottle):
    json_storage.upsert_bottle(sample_bottle)
    snap = json_storage.snapshot()
    snap["bottles"] = []
    assert len(json_storage.list_bottles()) == 1


def test_corrupt_json_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    st = JsonStorage(path)
    with pytest.raises(StorageError):
        st.load()


def test_populated_fixture(populated_json_storage):
    assert len(populated_json_storage.list_bottles()) == 3


def test_library_store_upsert(library_store, sample_bottle):
    library_store.upsert_bottle(sample_bottle)
    assert sample_bottle.id in library_store.bottles


def test_library_store_save_reload(library_store, sample_bottle):
    library_store.upsert_bottle(sample_bottle)
    library_store.save()
    library_store.load()
    assert sample_bottle.id in library_store.bottles


def test_library_store_to_dict(library_store, sample_bottle):
    library_store.upsert_bottle(sample_bottle)
    d = library_store.to_dict()
    assert d["version"] == SCHEMA_VERSION


def test_open_storage(tmp_path):
    p = tmp_path / "x.json"
    st = open_storage(str(p))
    assert st.path == p


def test_default_storage_path():
    p = default_storage_path()
    assert p.name == "library.json"


def test_replace_all(json_storage, sample_library_dict):
    json_storage.replace_all(sample_library_dict)
    assert len(json_storage.list_bottles()) == 3


def test_ensure_defaults_on_empty(json_storage):
    json_storage.raw_set("goals", None)
    json_storage.load()
    assert json_storage.raw_get("goals") is not None or json_storage.raw_get("goals") == []

from corklog.storage import LibraryFacade


def test_library_facade_add_bottle(tmp_library_path):
    lf = LibraryFacade(str(tmp_library_path))
    b = lf.add_bottle("Facade Bottle")
    assert b.title == "Facade Bottle"


def test_library_facade_log_tasting(tmp_library_path, sample_bottle):
    lf = LibraryFacade(str(tmp_library_path))
    lf.add_bottle(sample_bottle.title, id=sample_bottle.id, volume_ml=100)
    sess = lf.log_tasting(sample_bottle.id, 25, score=4.0)
    assert sess.ml_end == 25


def test_library_facade_stats_and_streak(tmp_library_path):
    lf = LibraryFacade(str(tmp_library_path))
    assert "Cellar stats" in lf.stats_text()
    assert isinstance(lf.streak_text(), str)


def test_library_facade_entity_summary(tmp_library_path):
    lf = LibraryFacade(str(tmp_library_path))
    assert "bottles" in lf.entity_summary()


def test_library_facade_find_bottle(tmp_library_path):
    lf = LibraryFacade(str(tmp_library_path))
    lf.add_bottle("Unique Title XYZ")
    found = lf.find_bottle("Unique")
    assert found is not None


def test_library_facade_mark_drunk(tmp_library_path):
    lf = LibraryFacade(str(tmp_library_path))
    b = lf.add_bottle("To Finish", volume_ml=50)
    lf.log_tasting(b.id, 50)
    done = lf.mark_drunk(b.id)
    assert done.status.value == "drunk"


def test_library_facade_import_export_csv(tmp_library_path, mini_csv, tmp_path):
    lf = LibraryFacade(str(tmp_library_path))
    n = lf.import_csv(mini_csv)
    assert n >= 1
    out = tmp_path / "out.csv"
    assert lf.export_csv(out) >= 1


def test_entity_dict_get_set_del(empty_storage, sample_bottle, sample_producer):
    empty_storage.upsert_producer(sample_producer)
    empty_storage.bottles[sample_bottle.id] = sample_bottle
    assert empty_storage.bottles[sample_bottle.id].title == sample_bottle.title
    del empty_storage.bottles[sample_bottle.id]
    with pytest.raises(NotFoundError):
        empty_storage.bottles[sample_bottle.id]
