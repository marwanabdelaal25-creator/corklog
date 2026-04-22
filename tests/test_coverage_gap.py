"""Broad coverage tests across the engine, CLI and utility layers."""

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from corklog.cli import main
from corklog.storage import LibraryStore, JsonStorage
from corklog.bottle import Bottle, CellarStatus
from corklog.producer import Producer
from corklog.tasting import Tasting
from corklog.errors import NotFoundError, ValidationError


# ---------------------------------------------------------------- CLI workflow

def _cli(data, *args):
    return main(["--data", str(data), *args])


def test_cli_full_workflow(tmp_path, capsys):
    data = tmp_path / "lib.json"
    assert _cli(data, "init") == 0
    assert _cli(data, "bottle-add", "Château Margaux", "--vintage", "2015",
                "--producer", "Château Margaux", "--varietal", "Cabernet Sauvignon",
                "--country", "France", "--price", "650", "--status", "cellared",
                "--drink-from", "2030", "--drink-to", "2055", "--lwin", "1011266") == 0
    assert _cli(data, "bottle-add", "Penfolds Grange", "--vintage", "2016", "--status", "open") == 0
    assert _cli(data, "bottle-list") == 0
    assert _cli(data, "bottle-list", "--status", "cellared", "--query", "Margaux") == 0
    assert _cli(data, "search", "Margaux") == 0
    assert _cli(data, "search", "--expr", "^Penfolds") == 0
    assert _cli(data, "stats") == 0
    assert _cli(data, "report", "year") == 0
    assert _cli(data, "report", "log") == 0
    assert _cli(data, "report", "md") == 0
    assert _cli(data, "report", "tonight") == 0
    assert _cli(data, "goal-add", "Drink 24", "--kind", "bottles", "--target", "24", "--period", "year") == 0
    assert _cli(data, "goal-list") == 0
    assert _cli(data, "tag-add", "first-growth", "--color", "#7b1e3a") == 0

    store = LibraryStore.open(data)
    bid = next(b.id for b in store.bottles.values() if "Margaux" in b.title)
    assert _cli(data, "tag-attach", bid, "first-growth") == 0
    assert _cli(data, "tasting-log", bid, "--pour", "150", "--score", "4.5", "--occasion", "dinner") == 0
    assert _cli(data, "rate", bid, "4.5", "--note", "Profound") == 0
    assert _cli(data, "bottle-show", bid) == 0
    assert _cli(data, "wishlist-add", "to-buy", bid) == 0
    assert _cli(data, "wishlist-list") == 0


def test_cli_import_export(tmp_path):
    data = tmp_path / "lib.json"
    _cli(data, "init")
    src = tmp_path / "imp.csv"
    src.write_text("title,vintage,status,varietal\nBrunello,2016,cellared,Sangiovese\n", encoding="utf-8")
    assert _cli(data, "import", str(src), "--format", "csv") == 0
    out_csv = tmp_path / "out.csv"
    assert _cli(data, "export", str(out_csv), "--format", "csv") == 0
    out_jsonl = tmp_path / "out.jsonl"
    assert _cli(data, "export", str(out_jsonl), "--format", "jsonl") == 0
    out_md = tmp_path / "out.md"
    assert _cli(data, "export", str(out_md), "--format", "md") == 0


def test_cli_import_unknown_format(tmp_path):
    data = tmp_path / "lib.json"
    _cli(data, "init")
    src = tmp_path / "x.dat"
    src.write_text("nope", encoding="utf-8")
    assert _cli(data, "import", str(src)) == 1  # fmt 'dat' from suffix is unknown


def test_cli_export_unknown_format(tmp_path):
    data = tmp_path / "lib.json"
    _cli(data, "init")
    assert _cli(data, "export", str(tmp_path / "o.zzz")) == 1


def test_cli_lwin_check(tmp_path):
    data = tmp_path / "lib.json"
    assert _cli(data, "lwin-check", "1011266") == 0
    assert _cli(data, "lwin-check", "garbage") == 1


def test_cli_backup_and_migrate(tmp_path):
    data = tmp_path / "lib.json"
    _cli(data, "init")
    _cli(data, "bottle-add", "Test Wine", "--vintage", "2019")
    assert _cli(data, "backup", "--dir", str(tmp_path / "bk")) == 0
    assert _cli(data, "migrate") == 0


def test_cli_bottle_rm(tmp_path):
    data = tmp_path / "lib.json"
    _cli(data, "init")
    _cli(data, "bottle-add", "Doomed", "--vintage", "2018")
    store = LibraryStore.open(data)
    bid = next(iter(store.bottles.values())).id
    assert _cli(data, "bottle-rm", bid) == 0


def test_cli_error_returns_two(tmp_path):
    data = tmp_path / "lib.json"
    _cli(data, "init")
    assert _cli(data, "bottle-show", "missing-id") == 2


@patch("urllib.request.urlopen")
def test_cli_fetch_lwin(mock_urlopen, tmp_path):
    payload = {"wines": [{"name": "Château Margaux", "vintage": 2015, "price": 650}]}
    m = MagicMock()
    m.read.return_value = json.dumps(payload).encode("utf-8")
    m.__enter__ = lambda s: s
    m.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = m
    data = tmp_path / "lib.json"
    _cli(data, "init")
    assert _cli(data, "fetch-lwin", "1011266") == 0


# ---------------------------------------------------------------- wishlist

def test_wishlist_manager(empty_storage):
    from corklog.wishlist import WishlistManager, Wishlist

    empty_storage.upsert_bottle(Bottle.create("Cellar Wine", id="b1"))
    wm = WishlistManager(empty_storage)
    wl = wm.create("Bordeaux dreams", description="big reds")
    assert wm.get(wl.id).name == "Bordeaux dreams"
    assert wm.find_by_name("bordeaux dreams").id == wl.id
    wm.add_bottle(wl.id, "b1")
    wm.add_bottle(wl.id, "b1")  # idempotent
    assert wm.get(wl.id).count() == 1
    wm.remove_bottle(wl.id, "b1")
    assert wm.get(wl.id).count() == 0
    assert "Bordeaux dreams" in wm.report(wl.id)
    assert wm.default_wishlist() is not None


def test_wishlist_get_missing(empty_storage):
    from corklog.wishlist import WishlistManager

    with pytest.raises(NotFoundError):
        WishlistManager(empty_storage).get("nope")


def test_wishlist_dataclass():
    from corklog.wishlist import Wishlist

    wl = Wishlist.create("My List")
    assert wl.slug == "my-list"
    assert wl.add_bottle("x") is True
    assert wl.add_bottle("x") is False
    assert wl.remove_bottle("x") is True
    assert wl.remove_bottle("x") is False
    wl2 = Wishlist.from_dict(wl.to_dict())
    assert wl2.name == "My List"


# ---------------------------------------------------------------- collections

def test_collections_manager(empty_storage):
    from corklog.collections import CollectionsManager, Collection

    empty_storage.upsert_bottle(Bottle.create("Cellar Wine", id="b1"))
    cm = CollectionsManager(empty_storage)
    c = cm.create("Verticals", description="same wine, many years")
    cm.add_bottle(c.id, "b1")
    cm.add_bottle(c.id, "b1")
    assert cm.bottles_in(c.id) == ["b1"]
    cm.remove_bottle(c.id, "b1")
    assert cm.bottles_in(c.id) == []
    assert cm.find_by_name("verticals").id == c.id
    assert cm.get(c.id).name == "Verticals"


def test_collection_dataclass():
    from corklog.collections import Collection

    c = Collection.create("C")
    c.add("a")
    assert c.includes("a") and c.size() == 1
    c.remove("a")
    assert not c.includes("a")
    assert Collection.from_dict(c.to_dict()).name == "C"


# ---------------------------------------------------------------- io_jsonl

def test_io_jsonl_roundtrip(populated_storage, tmp_path):
    from corklog import io_jsonl

    dest = tmp_path / "b.jsonl"
    n = io_jsonl.export_jsonl_bottles(populated_storage, dest)
    assert n == 3
    assert io_jsonl.count_lines(dest) == 3
    fresh = JsonStorage(tmp_path / "fresh.json")
    fresh.load()
    assert io_jsonl.import_jsonl_bottles(fresh, dest) == 3


def test_io_jsonl_tastings_and_full(populated_storage, tmp_path):
    from corklog import io_jsonl

    t = tmp_path / "t.jsonl"
    assert io_jsonl.export_jsonl_tastings(populated_storage, t) >= 1
    fresh = JsonStorage(tmp_path / "f2.json")
    fresh.load()
    assert io_jsonl.import_jsonl_tastings(fresh, t) >= 1
    full = tmp_path / "full.jsonl"
    io_jsonl.export_full_library(populated_storage, full)
    mixed = io_jsonl.import_mixed_jsonl(JsonStorage(tmp_path / "f3.json"), full)
    assert isinstance(mixed, dict)


# ---------------------------------------------------------------- recurring

def test_recurring_scheduler(empty_storage):
    from corklog.recurring import RecurringScheduler

    sch = RecurringScheduler(empty_storage)
    rule = sch.create("Weekly tasting", cadence="weekly", target_minutes=60)
    assert rule in sch.list_rules()
    sch.mark_done(rule.id)
    assert isinstance(sch.due_today(), list)
    assert isinstance(sch.overdue(), list)
    assert isinstance(sch.summary_text(), str)
    assert isinstance(sch.report(), str)
    sch.disable(rule.id)


def test_recurring_rule():
    from corklog.recurring import RecurringRule, due_rules, load_rules

    r = RecurringRule(id="r1", name="Daily pour", cadence="daily")
    assert r.due() in (True, False)
    r.mark_done()
    assert r.next_due() is not None
    rules = load_rules([r.to_dict()])
    assert len(rules) == 1
    assert isinstance(due_rules(rules), list)


# ---------------------------------------------------------------- producer mgr

def test_producer_manager(empty_storage):
    from corklog.producer import ProducerManager, sort_producers

    pm = ProducerManager(empty_storage)
    p = pm.create("Penfolds")
    assert pm.get(p.id).name == "Penfolds"
    assert pm.find_by_name("penfolds").id == p.id
    assert pm.find_or_create("Penfolds").id == p.id
    assert pm.find_or_create("Torbreck").name == "Torbreck"
    b = Bottle.create("Grange")
    empty_storage.upsert_bottle(b)
    pm.attach_bottle(p.id, b.id)
    assert b.id in pm.bottles_for(p.id)
    assert isinstance(pm.report(), str)
    assert isinstance(sort_producers(pm.list_all()), list)


def test_producer_methods():
    p = Producer.create("Winery", email="w@example.com")
    p.add_bottle("b1")
    p.add_bottle("b1")
    assert "b1" in p.bottle_ids
    p.remove_bottle("b1")
    p.merge_aliases(["Alt Name"])
    assert p.matches("winery")
    assert Producer.from_dict(p.to_dict()).name == "Winery"


# ---------------------------------------------------------------- quotes

def test_quotes_manager(populated_storage, sample_bottle):
    from corklog.quotes import QuotesManager, Quote

    populated_storage.upsert_bottle(sample_bottle)
    qm = QuotesManager(populated_storage)
    q = qm.add(Quote.create("Smells of tar and roses", sample_bottle.id, tags=["nose"]))
    assert qm.get(q.id).text.startswith("Smells")
    assert qm.list_for_bottle(sample_bottle.id)
    assert qm.search("tar")
    assert qm.by_tag("nose")
    assert qm.random_quote() is not None
    assert qm.daily_quote() is not None
    assert "tar" in qm.export_text()
    assert isinstance(qm.stats(), dict)
    qm.delete(q.id)


def test_quote_dataclass(sample_bottle):
    from corklog.quotes import Quote

    q = Quote.create("a fairly wordy tasting note here", sample_bottle.id)
    assert q.word_count() == 6
    assert q.preview(4)
    assert Quote.from_dict(q.to_dict()).text == q.text


# ---------------------------------------------------------------- parser

def test_parser_durations_and_dates():
    from corklog import parser

    assert parser.parse_duration("90") == 5400
    assert parser.parse_duration("1h30m") == 5400
    with pytest.raises(ValueError):
        parser.parse_duration("xx")
    assert parser.parse_date("2025-01-02").year == 2025
    assert parser.parse_date("today") == date.today()
    with pytest.raises(ValueError):
        parser.parse_date("nope")
    assert parser.parse_datetime("2025-01-02T10:00:00").hour == 10
    assert parser.parse_datetime("2025-01-02").hour == 0


def test_parser_progress_and_misc():
    from corklog import parser

    assert parser.parse_progress("150/750") == (150, 750)
    assert parser.parse_progress("45-320") == (45, 320)
    assert parser.parse_progress("100") == (100, None)
    assert parser.parse_key_value_pairs("a=1, b:2, junk") == {"a": "1", "b": "2"}
    assert parser.parse_key_value("k: v") == ("k", "v")
    with pytest.raises(ValueError):
        parser.parse_key_value("noseparator")
    assert parser.parse_tags("red; #bold, red") == ["red", "bold"]
    assert parser.parse_rating("4.5") == 4.5
    assert parser.parse_rating("90/100") == 4.5
    with pytest.raises(ValueError):
        parser.parse_rating("9")
    assert parser.split_csv_line('a,"b,c",d') == ["a", "b,c", "d"]
    assert parser.coerce_int("x", 7) == 7
    assert parser.coerce_bool("yes") is True
    assert parser.parse_bool("no") is False
    assert parser.format_duration(30) == "30m"
    assert parser.format_duration(90) == "1h 30m"
    assert parser.format_progress(150, 750) == "150-750"
    assert parser.format_progress(100) == "100"
    assert parser.human_join([]) == ""
    assert parser.human_join(["a"]) == "a"
    assert parser.human_join(["a", "b"]) == "a and b"
    assert "and" in parser.human_join(["a", "b", "c"])
    assert parser.parse_producer_list("A; B") == ["A", "B"]
    assert parser.parse_env_flag("on") is True
    assert parser.parse_env_flag("off") is False
    assert parser.parse_env_flag("maybe") is None
    assert parser.parse_import_format("gr") == "cellartracker"
    assert parser.parse_int_list("[1, 2, 3]") == [1, 2, 3]
    assert parser.parse_int_list("") == []
    assert parser.parse_page_range("10-20") == (10, 20)
    assert parser.parse_page_range("5") == (5, 5)
    assert parser.parse_sort_spec("-vintage") == ("vintage", False)
    assert parser.parse_year_range("2010-2020") == (2010, 2020)
    assert parser.parse_year_range("2015") == (2015, 2015)
    assert parser.tokenize_query("a b  c") == ["a", "b", "c"]


# ---------------------------------------------------------------- migrate

def test_migrate_v0_to_v2():
    from corklog import migrate

    data = {
        "version": 0,
        "bottles": [{"title": "Old", "status": "owned", "runtime": 750}],
    }
    assert migrate.needs_migration(data)
    out = migrate.migrate_data(data)
    assert out["version"] == migrate.SCHEMA_VERSION
    assert out["bottles"][0]["status"] == "cellared"
    assert isinstance(migrate.migration_plan(data), list)
    assert isinstance(migrate.describe(data), str)
    assert isinstance(migrate.validate_post_migration(out), list)


def test_migrate_helpers():
    from corklog import migrate

    rec = migrate.normalize_bottle_record({"status": "finished", "minutes": 750})
    assert rec["status"] == "drunk" and rec["volume_ml"] == 750
    data = {"bottles": [{"status": "drinking"}]}
    assert migrate.normalize_all_bottles(data) == 1
    before = {"version": 0, "bottles": []}
    after, snap = migrate.migrate_with_backup(before)
    assert "version" in migrate.diff_versions(before, after)
    assert migrate.backup_before_migrate(before)["version"] == 0


def test_migration_runner(populated_storage):
    from corklog.migrate import MigrationRunner

    runner = MigrationRunner(populated_storage)
    assert isinstance(runner.status(), str)
    assert isinstance(runner.preview(), dict)


# ---------------------------------------------------------------- backup

def test_backup_roundtrip(populated_storage, tmp_path):
    from corklog import backup

    out = backup.create_backup(populated_storage, tmp_path / "bk")
    assert out.exists()
    assert backup.verify_backup(out)
    assert backup.list_backups(tmp_path / "bk")
    target = tmp_path / "restored.json"
    backup.restore_backup(out, target)
    assert target.exists()


def test_backup_compressed_and_prune(populated_storage, tmp_path):
    from corklog import backup

    bkdir = tmp_path / "bk2"
    for _ in range(3):
        backup.create_backup(populated_storage, bkdir, compress=True)
    assert backup.checksum("hello") == backup.checksum("hello")
    pruned = backup.prune_old(bkdir, keep=1)
    assert pruned >= 0


# ---------------------------------------------------------------- search extras

def test_search_advanced_and_highlight(empty_storage):
    from corklog.search import SearchEngine

    b = Bottle.create("Barolo Riserva", varietal="Nebbiolo", status=CellarStatus.CELLARED)
    empty_storage.upsert_bottle(b)
    eng = SearchEngine(empty_storage)
    assert eng.advanced("status:cellared")
    assert eng.advanced("Barolo")
    assert "**Barolo**" in eng.highlight("Barolo Riserva", "Barolo")
    assert eng.regex_filter("Riserva", field="title")


def test_search_notes_quotes(populated_storage, sample_bottle):
    from corklog.search import SearchEngine
    from corklog.notes import Note
    from corklog.quotes import Quote

    populated_storage.upsert_bottle(sample_bottle)
    populated_storage.add_note(Note.create("oaky finish", sample_bottle.id, title="N"))
    populated_storage.add_quote(Quote.create("long legs on the glass", sample_bottle.id))
    eng = SearchEngine(populated_storage)
    assert eng.search_notes("oaky")
    assert eng.search_quotes("legs")


# ---------------------------------------------------------------- storage extras

def test_storage_crud_and_errors(empty_storage):
    b = Bottle.create("X", id="bx")
    empty_storage.upsert_bottle(b)
    assert empty_storage.get_bottle("bx").title == "X"
    with pytest.raises(NotFoundError):
        empty_storage.get_bottle("missing")
    empty_storage.delete_bottle("bx")
    assert empty_storage.list_bottles() == []
    snap = empty_storage.snapshot()
    assert "bottles" in snap
    assert isinstance(empty_storage.count_entities(), dict)


# ---------------------------------------------------------------- validators extras

def test_validators_branches():
    from corklog import validators as v

    assert v.validate_lwin_field(None) is None
    with pytest.raises(ValidationError):
        v.validate_lwin_field("not-valid")
    with pytest.raises(ValidationError):
        v.validate_progress(150.0)
    with pytest.raises(ValidationError):
        v.chk_id("x" * 65)
    assert v.validate_language("fr") == "fr"
    assert v.validate_language(None) == "en"
    with pytest.raises(ValidationError):
        v.validate_hex_color("nope")
    with pytest.raises(ValidationError):
        v.validate_positive_int(0, "n")
    with pytest.raises(ValidationError):
        v.validate_status("weird", ["ok"])
    assert v.sanitize_filename('a/b:c') == "a_b_c"
    assert v.soft_validate_slug("Big Reds!!") == "big-reds"
    assert v.validate_id_list(["a", "a", "b"]) == ["a", "b"]
    assert v.validate_percent(50.0) == 50.0
    assert v.validate_goal_target(5, "bottles") == 5
    assert v.merge_errors([ValidationError("x", field="f")])
    assert v.validate_url("https://x.io").startswith("https")
    with pytest.raises(ValidationError):
        v.validate_url("ftp://x")
