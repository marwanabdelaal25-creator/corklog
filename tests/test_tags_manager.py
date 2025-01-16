"""Tests for corklog.tags_manager."""

import pytest
from corklog.bottle import Bottle
from corklog.errors import NotFoundError, ValidationError
from corklog.tag import Tag
from corklog.tags_manager import TagsManager


def _store_with_bottle(library_store, sample_bottle):
    library_store.upsert_bottle(sample_bottle)
    return library_store


def test_list_all_empty(library_store):
    tm = TagsManager(library_store)
    assert tm.list_all() == []


def test_get_or_create(library_store):
    tm = TagsManager(library_store)
    t = tm.get_or_create("sci-fi")
    assert t.slug == "sci-fi"
    assert t.id in library_store.tags


def test_get_by_slug(library_store, sample_tag):
    library_store.tags[sample_tag.id] = sample_tag
    tm = TagsManager(library_store)
    assert tm.get_by_slug("burgundy").id == sample_tag.id


def test_get_by_slug_missing(library_store):
    assert TagsManager(library_store).get_by_slug("nope") is None


def test_rename(library_store, sample_tag):
    library_store.tags[sample_tag.id] = sample_tag
    tm = TagsManager(library_store)
    updated = tm.rename(sample_tag.id, "renamed-tag")
    assert updated.slug == "renamed-tag"


def test_rename_missing(library_store):
    with pytest.raises(NotFoundError):
        TagsManager(library_store).rename("missing", "x")


def test_delete(library_store, sample_tag):
    library_store.tags[sample_tag.id] = sample_tag
    TagsManager(library_store).delete(sample_tag.id)
    assert sample_tag.id not in library_store.tags


def test_delete_missing(library_store):
    with pytest.raises(NotFoundError):
        TagsManager(library_store).delete("nope")


def test_attach(library_store, sample_bottle, sample_tag):
    _store_with_bottle(library_store, sample_bottle)
    library_store.tags[sample_tag.id] = sample_tag
    tm = TagsManager(library_store)
    t = tm.get_or_create("new-tag")
    bk = tm.attach(sample_bottle.id, "new-tag")
    assert t.id in bk.tag_ids


def test_attach_missing_bottle(library_store):
    with pytest.raises(NotFoundError):
        TagsManager(library_store).attach("nope", "tag")


def test_detach(library_store, sample_bottle, sample_tag):
    sample_bottle.tag_ids.append(sample_tag.id)
    _store_with_bottle(library_store, sample_bottle)
    library_store.tags[sample_tag.id] = sample_tag
    TagsManager(library_store).detach(sample_bottle.id, sample_tag.id)
    assert sample_tag.id not in sample_bottle.tag_ids


def test_bottles_for_tag(library_store, sample_bottle, sample_tag):
    sample_bottle.tag_ids = [sample_tag.id]
    _store_with_bottle(library_store, sample_bottle)
    library_store.tags[sample_tag.id] = sample_tag
    bottles = TagsManager(library_store).bottles_for_tag("burgundy")
    assert len(bottles) == 1


def test_bottles_for_tag_unknown(library_store):
    assert TagsManager(library_store).bottles_for_tag("unknown") == []


def test_merge_tags(library_store, sample_bottle):
    t1 = Tag.create("a")
    t2 = Tag.create("b")
    sample_bottle.tag_ids = [t1.id, t2.id]
    _store_with_bottle(library_store, sample_bottle)
    library_store.tags[t1.id] = t1
    library_store.tags[t2.id] = t2
    TagsManager(library_store).merge_tags(t1.id, t2.id)
    assert t1.id not in library_store.tags
    assert t2.id in sample_bottle.tag_ids


def test_merge_self_raises(library_store, sample_tag):
    library_store.tags[sample_tag.id] = sample_tag
    with pytest.raises(ValidationError):
        TagsManager(library_store).merge_tags(sample_tag.id, sample_tag.id)


def test_unused(library_store, sample_tag):
    library_store.tags[sample_tag.id] = sample_tag
    unused = TagsManager(library_store).unused()
    assert sample_tag in unused


def test_attach_bumps_usage(library_store, sample_bottle):
    _store_with_bottle(library_store, sample_bottle)
    tm = TagsManager(library_store)
    tm.attach(sample_bottle.id, "fresh-tag")
    tag = tm.get_by_slug("fresh-tag")
    assert tag.usage_count >= 1


def test_list_all_sorted(library_store):
    for name in ("zebra", "alpha"):
        t = Tag.create(name)
        library_store.tags[t.id] = t
    names = [t.name for t in TagsManager(library_store).list_all()]
    assert names == sorted(names, key=str.lower)


def test_delete_removes_from_bottles(library_store, sample_bottle, sample_tag):
    sample_bottle.tag_ids = [sample_tag.id]
    _store_with_bottle(library_store, sample_bottle)
    library_store.tags[sample_tag.id] = sample_tag
    TagsManager(library_store).delete(sample_tag.id)
    assert sample_tag.id not in sample_bottle.tag_ids
