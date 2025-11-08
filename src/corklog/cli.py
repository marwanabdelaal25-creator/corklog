"""Command-line interface for corklog."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from corklog.storage import LibraryStore
from corklog.bottle import Bottle, CellarStatus
from corklog.producer import Producer
from corklog.tasting import Tasting, Session
from corklog.goals import GoalsManager, CellarGoal
from corklog.errors import CorklogError, NotFoundError
from corklog.audit_log import AuditLog
from corklog import search as search_mod
from corklog import stats as stats_mod
from corklog import streaks
from corklog import reports
from corklog import backup
from corklog import migrate
from corklog.tags_manager import TagsManager
from corklog import io_csv, io_cellartracker, io_vivino, io_jsonl, io_cellardb, io_winesearcher
from corklog.server import serve

__version__ = "0.1.0"


def _store_path(ns: argparse.Namespace) -> Path | None:
    return Path(ns.data) if getattr(ns, "data", None) else None


def _load(ns: argparse.Namespace) -> LibraryStore:
    p = _store_path(ns)
    return LibraryStore.open(p)


def _save(store: LibraryStore, ns: argparse.Namespace) -> None:
    store.save()
    if getattr(ns, "verbose", False):
        print("saved -> %s" % store.path)


def cmd_init(ns: argparse.Namespace) -> int:
    store = _load(ns)
    _save(store, ns)
    print("Initialized library at %s" % store.path)
    return 0


def cmd_bottle_add(ns: argparse.Namespace) -> int:
    store = _load(ns)
    bottle = Bottle.create(
        ns.title,
        lwin=ns.lwin,
        status=ns.status or "cellared",
        vintage=ns.vintage,
        varietal=ns.varietal or "",
        country=ns.country or "",
        price=ns.price,
        drink_from=ns.drink_from,
        drink_to=ns.drink_to,
    )
    if ns.volume_ml:
        bottle.volume_ml = int(ns.volume_ml)
    if ns.producer:
        au = next((a for a in store.producers.values() if a.name.lower() == ns.producer.lower()), None)
        if au is None:
            au = Producer.create(ns.producer)
            store.upsert_producer(au)
        bottle.producer_ids = [au.id]
    store.upsert_bottle(bottle)
    AuditLog(store._inner).log_create("bottle", bottle.id, title=bottle.title)
    _save(store, ns)
    print("Added %s (%s)" % (bottle.short_label(), bottle.id))
    return 0


def cmd_bottle_list(ns: argparse.Namespace) -> int:
    store = _load(ns)
    engine = search_mod.SearchEngine(store._inner)
    bottles = list(store.bottles.values())
    if ns.status:
        bottles = engine.filter_bottles(status=ns.status)
    if ns.query:
        hits = engine.search_bottles(ns.query)
        hit_ids = {h.id for h in hits}
        bottles = [b for b in bottles if b.id in hit_ids]
    bottles = sorted(bottles, key=lambda b: b.title.lower())
    if not bottles:
        print("No bottles found.")
        return 0
    for b in bottles[: ns.limit]:
        rating = b.rating_value if b.rating_value is not None else "-"
        print(
            "{id} | {title} | {st} | {pg}% | {rt}".format(
                id=b.id[:8],
                title=b.title[:50],
                st=b.status.value,
                pg=int(b.progress_pct()),
                rt=rating,
            )
        )
    return 0


def cmd_bottle_show(ns: argparse.Namespace) -> int:
    store = _load(ns)
    bk = store._inner.get_bottle(ns.id)
    print("Wine: %s" % bk.short_label())
    print("Status: %s | window: %s" % (bk.status.value, bk.drink_window_status()))
    if bk.varietal:
        print("Varietal: %s" % bk.varietal)
    if bk.country:
        print("Country: %s" % bk.country)
    if bk.price:
        print("Price: %.2f %s" % (bk.price, bk.currency))
    if bk.cellar_location:
        print("Location: %s" % bk.cellar_location)
    if bk.lwin:
        print("LWIN: %s" % bk.lwin)
    if bk.rating:
        print("Score: %s" % bk.rating.stars_display())
    if bk.description:
        print("\n%s" % bk.description[:500])
    return 0


def cmd_bottle_rm(ns: argparse.Namespace) -> int:
    store = _load(ns)
    store._inner.delete_bottle(ns.id)
    store.load()
    AuditLog(store._inner).log_delete("bottle", ns.id)
    _save(store, ns)
    print("Removed %s" % ns.id)
    return 0


def cmd_tasting_log(ns: argparse.Namespace) -> int:
    store = _load(ns)
    bk = store._inner.get_bottle(ns.bottle)
    ml_start = bk.ml_poured
    pour = ns.pour if ns.pour is not None else max(0, (bk.volume_ml or 0) - ml_start)
    ml_end = ml_start + max(0, pour)
    if bk.volume_ml:
        ml_end = min(ml_end, bk.volume_ml)
    sess = Tasting.create(
        bottle_id=bk.id,
        ml_start=ml_start,
        ml_end=ml_end,
        score=ns.score,
        occasion=ns.occasion or "",
    )
    store._inner.upsert_tasting(sess)
    bk.ml_poured = ml_end
    if bk.volume_ml and ml_end >= bk.volume_ml:
        bk.mark_finished()
    elif bk.status == CellarStatus.CELLARED:
        bk.mark_open()
    store.upsert_bottle(bk)
    AuditLog(store._inner).log_create("tasting", sess.id)
    _save(store, ns)
    print("Poured %dml of %s" % (sess.poured_ml(), bk.short_label()))
    return 0


def cmd_rate(ns: argparse.Namespace) -> int:
    from corklog.rating import Rating

    store = _load(ns)
    bk = store._inner.get_bottle(ns.bottle)
    bk.rating = ns.score
    store.upsert_bottle(bk)
    store._inner.add_rating(Rating.create(bk.id, value=ns.score, review=ns.note or ""))
    _save(store, ns)
    print("Scored %s: %.1f/5" % (bk.short_label(), ns.score))
    return 0


def cmd_wishlist_list(ns: argparse.Namespace) -> int:
    store = _load(ns)
    wishlists = sorted(store._inner.list_wishlists(), key=lambda s: s.sort_order)
    for sh in wishlists:
        print("%s | %s (%d)" % (sh.id[:8], sh.name, sh.count()))
    return 0


def cmd_wishlist_add_bottle(ns: argparse.Namespace) -> int:
    store = _load(ns)
    wishlists = {s.id: s for s in store._inner.list_wishlists()}
    sh = wishlists.get(ns.wishlist)
    if sh is None:
        sh = next((s for s in wishlists.values() if s.id.startswith(ns.wishlist)), None)
    if sh is None:
        sh = next((s for s in wishlists.values() if s.name.lower() == ns.wishlist.lower()), None)
    if sh is None:
        from corklog.wishlist import Wishlist

        sh = Wishlist.create(ns.wishlist)
        store._inner.upsert_wishlist(sh)
    store._inner.get_bottle(ns.bottle)
    sh.add_bottle(ns.bottle)
    store._inner.upsert_wishlist(sh)
    _save(store, ns)
    print("Added to wishlist %s" % sh.name)
    return 0


def cmd_search(ns: argparse.Namespace) -> int:
    store = _load(ns)
    engine = search_mod.SearchEngine(store._inner)
    if ns.expr:
        bottles = engine.regex_filter(ns.expr)
    else:
        hits = engine.search_bottles(ns.query or "")
        id_map = {b.id: b for b in store.bottles.values()}
        bottles = [id_map[h.id] for h in hits if h.id in id_map]
    for b in bottles[:50]:
        print("%s — %s" % (b.id[:8], b.title))
    print("%d result(s)" % len(bottles))
    return 0


def cmd_stats(ns: argparse.Namespace) -> int:
    store = _load(ns)
    print(stats_mod.format_stats(store._inner))
    print(streaks.streak_summary(store))
    return 0


def cmd_report(ns: argparse.Namespace) -> int:
    store = _load(ns)
    rb = reports.ReportBuilder(store._inner)
    if ns.kind == "year":
        print(rb.yearly_summary(ns.year))
    elif ns.kind == "log":
        print(rb.status_report())
    elif ns.kind == "tonight":
        print(rb.drink_tonight())
    else:
        print(rb.export_text())
    return 0


def cmd_goal_add(ns: argparse.Namespace) -> int:
    store = _load(ns)
    gm = GoalsManager(store._inner)
    g = CellarGoal.create(ns.name, ns.kind, int(ns.target), ns.period)
    gm.add_goal(g)
    _save(store, ns)
    print("Goal created: %s" % g.id)
    return 0


def cmd_goal_list(ns: argparse.Namespace) -> int:
    store = _load(ns)
    gm = GoalsManager(store._inner)
    for g in gm.refresh_all():
        print(
            "{name}: {prog}/{tgt} ({pct:.0f}%)".format(
                name=g.name, prog=g.progress, tgt=g.target, pct=g.pct_complete()
            )
        )
    return 0


def cmd_tag_add(ns: argparse.Namespace) -> int:
    store = _load(ns)
    tm = TagsManager(store._inner)
    tag = tm.create(ns.name, color=ns.color or "#6b7280")
    _save(store, ns)
    print("Tag %s (%s)" % (tag.name, tag.id))
    return 0


def cmd_tag_attach(ns: argparse.Namespace) -> int:
    store = _load(ns)
    tm = TagsManager(store._inner)
    tag = tm.find_or_create(ns.tag)
    tm.attach(ns.bottle, tag.id)
    _save(store, ns)
    return 0


def cmd_import(ns: argparse.Namespace) -> int:
    store = _load(ns)
    src = Path(ns.file)
    fmt = ns.format or src.suffix.lstrip(".").lower()
    n = 0
    if fmt == "csv":
        n = io_csv.import_csv(store, src)
    elif fmt == "cellartracker":
        n = io_cellartracker.import_cellartracker(store, src)
    elif fmt == "vivino":
        n = io_vivino.import_vivino(store, src)
    elif fmt == "jsonl":
        n = io_jsonl.import_jsonl_bottles(store, src)
    elif fmt == "cellardb":
        n = io_cellardb.import_cellardb(store, Path(ns.file))
    else:
        print("Unknown format: %s" % fmt, file=sys.stderr)
        return 1
    _save(store, ns)
    print("Imported %d record(s)" % n)
    return 0


def cmd_export(ns: argparse.Namespace) -> int:
    store = _load(ns)
    dest = Path(ns.file)
    fmt = ns.format or dest.suffix.lstrip(".").lower()
    if fmt == "csv":
        n = io_csv.export_csv(store, dest)
    elif fmt == "jsonl":
        n = io_jsonl.export_jsonl_bottles(store, dest)
    elif fmt == "md":
        dest.write_text(reports.ReportBuilder(store._inner).export_text(), encoding="utf-8")
        n = len(store.bottles)
    else:
        print("Unknown export format", file=sys.stderr)
        return 1
    print("Exported %d" % n)
    return 0


def cmd_lwin_check(ns: argparse.Namespace) -> int:
    from corklog.lwin import validate_lwin

    if validate_lwin(ns.lwin):
        print("valid: %s" % ns.lwin)
        return 0
    print("invalid: %s" % ns.lwin, file=sys.stderr)
    return 1


def cmd_fetch_lwin(ns: argparse.Namespace) -> int:
    store = _load(ns)
    bottle = io_winesearcher.bottle_from_lwin(ns.lwin)
    store.upsert_bottle(bottle)
    _save(store, ns)
    print("Fetched: %s" % bottle.title)
    return 0


def cmd_backup(ns: argparse.Namespace) -> int:
    store = _load(ns)
    dest = Path(ns.dir) if ns.dir else None
    out = backup.create_backup(store, dest, compress=ns.gzip)
    print("Backup -> %s" % out)
    return 0


def cmd_restore(ns: argparse.Namespace) -> int:
    store = _load(ns)
    backup.restore_backup(Path(ns.file), store.path)
    store.load()
    print("Restored from %s" % ns.file)
    return 0


def cmd_serve(ns: argparse.Namespace) -> int:
    store = _load(ns)
    serve(store._inner, host=ns.host, port=ns.port)
    return 0


def cmd_migrate(ns: argparse.Namespace) -> int:
    store = _load(ns)
    data = store.to_dict()
    if not migrate.needs_migration(data):
        print("Already at schema v%d" % data.get("version", 1))
        return 0
    new_data = migrate.migrate_data(data)
    store._inner.replace_all(new_data)
    store.load()
    _save(store, ns)
    print("Migrated to v%d" % new_data.get("version", 1))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="corklog", description="Personal wine cellar & tasting log")
    p.add_argument("--data", help="Path to library.json")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--version", action="version", version="%(prog)s " + __version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init", help="Create empty library")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("bottle-add", help="Add a bottle to the cellar")
    sp.add_argument("title")
    sp.add_argument("--lwin")
    sp.add_argument("--producer")
    sp.add_argument("--vintage", type=int)
    sp.add_argument("--varietal")
    sp.add_argument("--country")
    sp.add_argument("--price", type=float)
    sp.add_argument("--drink-from", dest="drink_from", type=int)
    sp.add_argument("--drink-to", dest="drink_to", type=int)
    sp.add_argument("--status", choices=["want", "cellared", "open", "drunk", "dumped"])
    sp.add_argument("--volume-ml", dest="volume_ml", type=int, help="Bottle volume in ml (default 750)")
    sp.set_defaults(func=cmd_bottle_add)

    sp = sub.add_parser("bottle-list", help="List bottles")
    sp.add_argument("-q", "--query", default="")
    sp.add_argument("--status")
    sp.add_argument("--limit", type=int, default=100)
    sp.set_defaults(func=cmd_bottle_list)

    sp = sub.add_parser("bottle-show", help="Show bottle details")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_bottle_show)

    sp = sub.add_parser("bottle-rm", help="Remove a bottle")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_bottle_rm)

    sp = sub.add_parser("tasting-log", help="Log a tasting (a pour from a bottle)")
    sp.add_argument("bottle", help="Bottle id")
    sp.add_argument("--pour", type=int, help="Amount poured in ml (default: the rest of the bottle)")
    sp.add_argument("--score", type=float, help="Your score 0-5")
    sp.add_argument("--occasion")
    sp.set_defaults(func=cmd_tasting_log)

    sp = sub.add_parser("rate", help="Score a bottle 0-5")
    sp.add_argument("bottle")
    sp.add_argument("score", type=float)
    sp.add_argument("--note", help="A short review")
    sp.set_defaults(func=cmd_rate)

    sp = sub.add_parser("wishlist-list")
    sp.set_defaults(func=cmd_wishlist_list)

    sp = sub.add_parser("wishlist-add")
    sp.add_argument("wishlist")
    sp.add_argument("bottle")
    sp.set_defaults(func=cmd_wishlist_add_bottle)

    sp = sub.add_parser("search")
    sp.add_argument("query", nargs="?", default="")
    sp.add_argument("--expr", help="Advanced query")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("stats")
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("report")
    sp.add_argument("kind", choices=["year", "log", "md", "tonight"], default="year", nargs="?")
    sp.add_argument("--year", type=int)
    sp.add_argument("--limit", type=int, default=20)
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("goal-add")
    sp.add_argument("name")
    sp.add_argument("--kind", default="bottles", choices=["bottles", "volume_ml", "tastings"])
    sp.add_argument("--target", default="12")
    sp.add_argument("--period", default="year")
    sp.set_defaults(func=cmd_goal_add)

    sp = sub.add_parser("goal-list")
    sp.set_defaults(func=cmd_goal_list)

    sp = sub.add_parser("tag-add")
    sp.add_argument("name")
    sp.add_argument("--color", default="#6b7280")
    sp.set_defaults(func=cmd_tag_add)

    sp = sub.add_parser("tag-attach")
    sp.add_argument("bottle")
    sp.add_argument("tag")
    sp.set_defaults(func=cmd_tag_attach)

    sp = sub.add_parser("import")
    sp.add_argument("file")
    sp.add_argument("--format", choices=["csv", "cellartracker", "vivino", "jsonl", "cellardb"])
    sp.set_defaults(func=cmd_import)

    sp = sub.add_parser("export")
    sp.add_argument("file")
    sp.add_argument("--format", choices=["csv", "jsonl", "md"])
    sp.set_defaults(func=cmd_export)

    sp = sub.add_parser("fetch-lwin")
    sp.add_argument("lwin")
    sp.set_defaults(func=cmd_fetch_lwin)

    sp = sub.add_parser("lwin-check")
    sp.add_argument("lwin")
    sp.set_defaults(func=cmd_lwin_check)

    sp = sub.add_parser("backup")
    sp.add_argument("--dir")
    sp.add_argument("--gzip", action="store_true")
    sp.set_defaults(func=cmd_backup)

    sp = sub.add_parser("restore")
    sp.add_argument("file")
    sp.set_defaults(func=cmd_restore)

    sp = sub.add_parser("serve")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8765)
    sp.set_defaults(func=cmd_serve)

    sp = sub.add_parser("migrate")
    sp.set_defaults(func=cmd_migrate)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    ns = parser.parse_args(argv)
    try:
        return ns.func(ns)
    except CorklogError as exc:
        print("error: %s" % exc.message, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
