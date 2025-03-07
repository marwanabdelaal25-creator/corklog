"""Tests for corklog.search."""

import pytest
from corklog.bottle import Bottle, CellarStatus
from corklog.search import SearchEngine, SearchHit, _score, _norm


def test_norm_collapses_whitespace():
    assert _norm("  Hello   World ") == "hello world"


def test_score_exact_match():
    assert _score("barolo", "Barolo") == 1.0


def test_score_substring():
    assert _score("left", "The Left Hand of Darkness") > 0.5


def test_score_no_match():
    assert _score("xyz", "abc") == 0.0


def test_search_bottles_title(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    hits = eng.search_bottles("Margaux")
    assert hits[0].title == "Château Margaux"


def test_search_bottles_lwin(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    hits = eng.search_bottles("1011266")
    assert hits and hits[0].score >= 0.9


def test_search_bottles_limit(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    hits = eng.search_bottles("e", limit=1)
    assert len(hits) <= 1


def test_search_producers(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    hits = eng.search_producers("Penfolds")
    assert hits and hits[0].kind == "producer"


def test_search_all_combines(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    hits = eng.search_all("Penfolds")
    kinds = {h.kind for h in hits}
    assert "producer" in kinds or "bottle" in kinds


def test_filter_bottles_status(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    bottles = eng.filter_bottles(status="want")
    assert all(b.status == CellarStatus.WANT for b in bottles)


def test_filter_bottles_tag(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    bottles = eng.filter_bottles(tag_id="tag-001")
    assert len(bottles) >= 1


def test_filter_bottles_wishlist(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    bottles = eng.filter_bottles(wishlist_id="wishlist-001")
    assert len(bottles) >= 1


def test_regex_filter_title(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    bottles = eng.regex_filter("^Penfolds")
    assert len(bottles) == 1


def test_regex_filter_no_match(populated_json_storage):
    eng = SearchEngine(populated_json_storage)
    assert eng.regex_filter("^ZZZZZ") == []


def test_search_hit_fields():
    h = SearchHit("bottle", "id1", "Title", 0.9, "snippet")
    assert h.score == 0.9


def test_search_empty_query(json_storage, sample_bottle):
    json_storage.upsert_bottle(sample_bottle)
    eng = SearchEngine(json_storage)
    assert eng.search_bottles("") == []


def test_search_bottles_sorted_by_score(json_storage):
    for title in ["Alpha Bottle", "Beta Bottle", "Alphabet Soup"]:
        json_storage.upsert_bottle(Bottle.create(title))
    hits = SearchEngine(json_storage).search_bottles("Alpha")
    assert hits[0].score >= hits[-1].score


def test_filter_bottles_no_filters(populated_json_storage):
    bottles = SearchEngine(populated_json_storage).filter_bottles()
    assert len(bottles) == 3


def test_search_producers_low_score_filtered(populated_json_storage):
    hits = SearchEngine(populated_json_storage).search_producers("zzzzzzz")
    assert hits == []


def test_regex_filter_description(json_storage):
    b = Bottle.create("X", description="unique phrase here")
    json_storage.upsert_bottle(b)
    hits = SearchEngine(json_storage).regex_filter("unique phrase", field="description")
    assert len(hits) == 1

from corklog.notes import Note
from corklog.quotes import Quote
from corklog.search import SearchEngine, SearchHit, _score


def test_score_exact_match():
    assert _score("hello", "hello") == 1.0


def test_score_empty():
    assert _score("", "text") == 0.0


def test_search_producers(populated_storage, sample_producer):
    populated_storage.upsert_producer(sample_producer)
    hits = SearchEngine(populated_storage).search_producers(sample_producer.name)
    assert hits and hits[0].kind == "producer"


def test_search_notes(populated_storage, sample_bottle):
    populated_storage.add_note(Note.create("needle body", sample_bottle.id, title="T"))
    hits = SearchEngine(populated_storage).search_notes("needle")
    assert len(hits) >= 1


def test_search_quotes(populated_storage, sample_bottle):
    populated_storage.add_quote(Quote(text="to be or not", bottle_id=sample_bottle.id))
    hits = SearchEngine(populated_storage).search_quotes("be or")
    assert len(hits) >= 1


def test_search_all(populated_storage):
    hits = SearchEngine(populated_storage).search_all("Margaux")
    assert isinstance(hits, list)


def test_filter_bottles_by_tag(empty_storage, sample_bottle, sample_tag):
    sample_bottle.tag_ids = [sample_tag.id]
    empty_storage.upsert_tag(sample_tag)
    empty_storage.upsert_bottle(sample_bottle)
    bottles = SearchEngine(empty_storage).filter_bottles(tag_id=sample_tag.id)
    assert len(bottles) == 1


def test_advanced_status(empty_storage, sample_bottle):
    empty_storage.upsert_bottle(sample_bottle)
    pool = SearchEngine(empty_storage).advanced("status:open")
    assert len(pool) >= 1


def test_advanced_title_token(empty_storage, sample_bottle):
    empty_storage.upsert_bottle(sample_bottle)
    pool = SearchEngine(empty_storage).advanced("Barolo")
    assert pool


def test_highlight(empty_storage):
    assert "**foo**" in SearchEngine(empty_storage).highlight("foo bar", "foo")
