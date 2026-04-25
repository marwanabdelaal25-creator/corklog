"""Second coverage pass: search DSL, storage internals, migrate, plugins, recurring."""

import sqlite3
from datetime import date

import pytest

from corklog.bottle import Bottle, CellarStatus
from corklog.producer import Producer
from corklog.tag import Tag
from corklog.tasting import Tasting
from corklog.rating import Rating
from corklog.errors import NotFoundError, PluginError


# ----------------------------------------------------------------- search DSL

def test_search_advanced_all_branches(empty_storage):
    from corklog.search import SearchEngine

    empty_storage.upsert_tag(Tag.create("bold", id="t1"))
    b = Bottle.create("Barolo Riserva", varietal="Nebbiolo", lwin="1011266", status=CellarStatus.CELLARED)
    b.tag_ids = ["t1"]
    empty_storage.upsert_bottle(b)
    eng = SearchEngine(empty_storage)
    assert eng.advanced("tag:bold")
    assert eng.advanced("title:barolo")
    assert eng.advanced("lwin:1011266")
    assert isinstance(eng.advanced("tag:doesnotexist"), list)  # tid None branch


def test_search_highlight_empty(empty_storage):
    from corklog.search import SearchEngine

    assert SearchEngine(empty_storage).highlight("text", "") == "text"


def test_search_suggest(empty_storage):
    from corklog.search import SearchEngine

    for t in ["Barolo", "Barbaresco", "Chianti"]:
        empty_storage.upsert_bottle(Bottle.create(t))
    eng = SearchEngine(empty_storage)
    assert "Barolo" in eng.suggest("Bar")
    assert any("Chianti" in x for x in eng.suggest("anti"))  # substring fallback


def test_search_recent_bottles(empty_storage):
    from corklog.search import SearchEngine

    fresh = Bottle.create("Recent")
    fresh.started_at = date.today().isoformat()
    empty_storage.upsert_bottle(fresh)
    old = Bottle.create("Old")
    old.started_at = "2000-01-01"
    empty_storage.upsert_bottle(old)
    bad = Bottle.create("Bad")
    bad.started_at = "notadate"
    empty_storage.upsert_bottle(bad)
    out = SearchEngine(empty_storage).recent_bottles(days=30)
    assert any(b.title == "Recent" for b in out)


# ----------------------------------------------------------------- storage

def test_storage_missing_lookups(empty_storage):
    with pytest.raises(NotFoundError):
        empty_storage.get_producer("nope")
    with pytest.raises(NotFoundError):
        empty_storage.get_wishlist("nope")


def test_storage_delete_paths(empty_storage):
    empty_storage.upsert_producer(Producer.create("P", id="p1"))
    empty_storage.delete_producer("p1")
    assert empty_storage.list_producers() == []
    empty_storage.upsert_tag(Tag.create("x", id="tg"))
    empty_storage.delete_tag("tg")
    empty_storage.add_tasting(Tasting.create("b", id="ta1"))
    empty_storage.delete_tasting("ta1")
    assert empty_storage.list_tastings() == []


def test_storage_raw_and_filtered_lists(empty_storage):
    from corklog.quotes import Quote
    from corklog.notes import Note

    empty_storage.raw_set("foo", 42)
    assert empty_storage.raw_get("foo") == 42
    b = Bottle.create("B", id="bb")
    empty_storage.upsert_bottle(b)
    empty_storage.add_rating(Rating.create("bb", value=4.0))
    assert empty_storage.list_ratings("bb")
    empty_storage.add_quote(Quote.create("q text", "bb"))
    assert empty_storage.list_quotes("bb")
    empty_storage.add_note(Note.create("note body", "bb"))
    assert empty_storage.list_notes("bb")


def test_storage_region_vertical_collection(empty_storage):
    from corklog.regions import Region
    from corklog.vertical import Vertical
    from corklog.collections import Collection

    empty_storage.upsert_region(Region.create("Bordeaux"))
    assert empty_storage.list_regions()
    empty_storage.upsert_vertical(Vertical.create("Margaux vertical"))
    assert empty_storage.list_vertical()
    empty_storage.upsert_collection(Collection.create("Cellar picks"))
    assert empty_storage.list_collections()


def test_storage_tastings_by_bottle(empty_storage):
    empty_storage.add_tasting(Tasting.create("b1", id="t1", ml_start=0, ml_end=50))
    empty_storage.add_tasting(Tasting.create("b2", id="t2", ml_start=0, ml_end=50))
    assert len(empty_storage.list_tastings("b1")) == 1


# ----------------------------------------------------------------- migrate run

def test_migration_runner_run(tmp_path):
    from corklog.storage import JsonStorage
    from corklog.migrate import MigrationRunner

    st = JsonStorage(tmp_path / "m.json")
    st.load()
    st.replace_all({
        "version": 0,
        "bottles": [{"title": "Old", "status": "owned", "runtime": 750}],
        "producers": [], "tastings": [], "tags": [],
    })
    result = MigrationRunner(st).run()
    assert "after" in result


def test_apply_to_file(tmp_path):
    from corklog.storage import JsonStorage
    from corklog import migrate

    st = JsonStorage(tmp_path / "a.json")
    st.load()
    st.replace_all({"version": 0, "bottles": [], "producers": [], "tastings": [], "tags": []})
    assert migrate.apply_to_file(st) is True


def test_migrate_rollback(tmp_path):
    from corklog import migrate

    target = tmp_path / "rb.json"
    migrate.rollback({"version": 1, "bottles": []}, target)
    assert target.exists()


def test_migrate_validate_warnings():
    from corklog import migrate

    warns = migrate.validate_post_migration({"version": 99})
    assert isinstance(warns, list)


# ----------------------------------------------------------------- recurring

def test_recurring_overdue_and_streak(empty_storage):
    from corklog.recurring import RecurringScheduler, RecurringRule

    sch = RecurringScheduler(empty_storage)
    rule = sch.create("Cellar check", cadence="daily")
    sch.mark_done(rule.id, when=date(2020, 1, 1))  # long ago -> overdue
    assert isinstance(sch.overdue(), list)
    reloaded = sch.list_rules()[0]
    assert reloaded.streak_days() >= 0
    sch.disable(rule.id)
    assert all(not r.enabled for r in sch.list_rules())


def test_recurring_rule_next_due_cadences():
    from corklog.recurring import RecurringRule

    for cadence in ("daily", "weekly", "monthly"):
        r = RecurringRule(id="r", name="n", cadence=cadence)
        r.mark_done(date(2025, 1, 1))
        assert r.next_due() > date(2025, 1, 1)


# ----------------------------------------------------------------- plugins

def _plugin(name="p", hook="on_bottle_add"):
    from corklog.plugins import Plugin

    return Plugin(name=name, module="m", hooks={hook: lambda *a, **k: "ok-%s" % name})


def test_plugin_manager(capsys):
    from corklog.plugins import PluginManager

    pm = PluginManager()
    pm.register(_plugin("p1"))
    assert pm.run_hook("on_bottle_add") == ["ok-p1"]
    safe = pm.run_hook_safe("on_bottle_add")
    assert safe[0].value == "ok-p1"
    assert "p1" in pm.list_plugins()
    assert isinstance(pm.describe(), str)
    pm.disable("p1")
    assert pm.run_hook("on_bottle_add") == []
    pm.enable("p1")
    pm.unload("p1")
    assert pm.list_plugins() == []


def test_plugin_hook_error():
    from corklog.plugins import Plugin, PluginManager

    boom = Plugin(name="boom", module="m", hooks={"on_bottle_add": lambda *a, **k: 1 / 0})
    pm = PluginManager()
    pm.register(boom)
    with pytest.raises(PluginError):
        pm.run_hook("on_bottle_add")
    results = pm.run_hook_safe("on_bottle_add")
    assert results[0].error is not None


def test_plugin_load_module_failure():
    from corklog.plugins import PluginManager

    with pytest.raises(PluginError):
        PluginManager().load_module("corklog.__definitely_not_real__")


def test_register_hook_module_level():
    from corklog import plugins

    plugins.register_hook("on_bottle_add", lambda *a, **k: None, plugin_name="inline")
    assert isinstance(plugins.list_plugins(), list)


# ----------------------------------------------------------------- tags manager

def test_tags_manager_full(empty_storage):
    from corklog.tags_manager import TagsManager

    tm = TagsManager(empty_storage)
    b = Bottle.create("B", id="bb")
    empty_storage.upsert_bottle(b)
    t1 = tm.create("first-growth")
    tm.attach("bb", t1.name)
    assert tm.tags_for_bottle("bb")
    assert tm.usage_counts().get("first-growth") == 1
    tm.detach("bb", t1.id)
    t2 = tm.create("second")
    b2 = Bottle.create("B2", id="b2")
    b2.tag_ids = [t1.id, t2.id]
    empty_storage.upsert_bottle(b2)
    kept = tm.merge_tags(t2.id, t1.id)
    assert kept.id == t1.id
    assert isinstance(tm.unused(), list)
    renamed = tm.rename(t1.id, "renamed")
    assert renamed.slug == "renamed"
    assert tm.get_by_slug("nope") is None


# ----------------------------------------------------------------- io_cellardb tags

def test_io_cellardb_with_tags(library_store, tmp_path):
    from corklog import io_cellardb

    lib = tmp_path / "cellar"
    lib.mkdir()
    conn = sqlite3.connect(str(lib / "cellar.db"))
    conn.execute("CREATE TABLE bottles (id INTEGER PRIMARY KEY, wine TEXT, vintage TEXT, lwin TEXT, varietal TEXT, country TEXT, price REAL)")
    conn.execute("CREATE TABLE producers (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("CREATE TABLE bottles_producers_link (bottle INTEGER, producer INTEGER)")
    conn.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, bottle INTEGER, text TEXT)")
    conn.execute("CREATE TABLE tags (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("CREATE TABLE bottles_tags_link (bottle INTEGER, tag INTEGER)")
    conn.execute("INSERT INTO bottles VALUES (1,'Barolo','2016','1011266','Nebbiolo','Italy',80.0)")
    conn.execute("INSERT INTO tags VALUES (1,'piedmont')")
    conn.execute("INSERT INTO bottles_tags_link VALUES (1,1)")
    conn.commit()
    conn.close()
    assert io_cellardb.import_cellardb(library_store, lib) == 1
    bottle = next(iter(library_store.bottles.values()))
    assert bottle.tag_ids


# ----------------------------------------------------------------- entity edges

def test_bottle_from_dict_rating_object():
    b = Bottle.create("X")
    b.rating = Rating.create(b.id, value=4.0, review="great")
    restored = Bottle.from_dict(b.to_dict())
    assert restored.rating_value == 4.0


def test_bottle_years_to_window_unknown():
    assert Bottle.create("X").years_to_window(2026) == 0


def test_quotes_random_empty(empty_storage):
    from corklog.quotes import QuotesManager

    assert QuotesManager(empty_storage).random_quote() is None
    assert QuotesManager(empty_storage).daily_quote() is None


# ----------------------------------------------------------------- more CLI

def _cli(data, *args):
    from corklog.cli import main
    return main(["--data", str(data), *args])


def test_cli_restore_and_migrate_noop(tmp_path):
    data = tmp_path / "lib.json"
    _cli(data, "init")
    _cli(data, "bottle-add", "Keeper", "--vintage", "2018")
    bkdir = tmp_path / "bk"
    _cli(data, "backup", "--dir", str(bkdir))
    from corklog import backup as bk
    backups = bk.list_backups(bkdir)
    assert _cli(data, "restore", str(backups[0])) == 0
    assert _cli(data, "migrate") == 0  # already current schema


def test_cli_bottle_list_with_rating(tmp_path):
    data = tmp_path / "lib.json"
    _cli(data, "init")
    from corklog.storage import LibraryStore
    store = LibraryStore.open(data)
    b = Bottle.create("Rated Wine", vintage=2015)
    b.rating = 4.5
    store.upsert_bottle(b)
    store.save()
    assert _cli(data, "bottle-list") == 0


# ----------------------------------------------------------------- facade

def test_library_facade_methods(tmp_path):
    from corklog.storage import LibraryFacade

    lf = LibraryFacade(str(tmp_path / "lib.json"))
    lf.add_bottle("Open One", id="o1", volume_ml=750, status=CellarStatus.OPEN)
    lf.add_bottle("Open Two", id="o2", status=CellarStatus.OPEN)
    assert len(lf.list_open()) == 2
    assert lf.find_bottle("Open One") is not None
    assert lf.find_bottle("nonexistent zzz") is None
    drunk = lf.mark_drunk("o1")
    assert drunk.status == CellarStatus.DRUNK
    assert lf.path().name == "lib.json"
    csv_path = tmp_path / "exp.csv"
    assert lf.export_csv(csv_path) >= 1
    assert lf.import_csv(csv_path) >= 1
    assert "bottles" in lf.entity_summary()


def test_facade_backup(tmp_path):
    from corklog.storage import LibraryFacade

    lf = LibraryFacade(str(tmp_path / "lib.json"))
    lf.add_bottle("X")
    out = lf.backup(tmp_path / "bk2")
    assert out.exists()


# ----------------------------------------------------------------- wishlist report

def test_wishlist_report_missing_bottle(empty_storage):
    from corklog.wishlist import WishlistManager

    wm = WishlistManager(empty_storage)
    wl = wm.create("Orphans")
    wl.add_bottle("ghost-id")
    empty_storage.upsert_wishlist(wl)
    assert "missing" in wm.report(wl.id)


def test_validators_chk_id_ok():
    from corklog import validators as v

    assert v.chk_id("fine-id") == "fine-id"
