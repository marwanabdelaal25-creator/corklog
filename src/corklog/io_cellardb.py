"""Import from a local sqlite cellar database (e.g. the CellarTracker desktop
app, or any tool that keeps a ``cellar.db``)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, List

from corklog.producer import Producer
from corklog.bottle import Bottle, CellarStatus
from corklog.errors import ImportError as CorklogImportError
from corklog.storage import JsonStorage


def _read_db(library: Path) -> Path:
    db = library / "cellar.db"
    if not db.exists():
        raise CorklogImportError("cellardb", "cellar.db not found in %s" % library)
    return db


def _tags_for_bottle(conn: sqlite3.Connection, bottle_id: int) -> List[str]:
    try:
        cur = conn.execute(
            """
            SELECT tags.name FROM tags
            JOIN bottles_tags_link ON bottles_tags_link.tag = tags.id
            WHERE bottles_tags_link.bottle = ?
            """,
            (bottle_id,),
        )
        return [r[0] for r in cur.fetchall()]
    except sqlite3.OperationalError:
        return []


def _safe_lwin(raw) -> str | None:
    from corklog.lwin import validate_lwin
    if raw and validate_lwin(str(raw)):
        return str(raw)
    return None


def import_cellardb(storage: JsonStorage, library_path: Path) -> int:
    db = _read_db(library_path)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT b.id, b.wine, b.vintage, b.lwin, b.varietal, b.country, b.price,
               c.text AS note
        FROM bottles b
        LEFT JOIN notes c ON c.bottle = b.id
        """
    )
    n = 0
    for row in cur:
        title = row["wine"] or "Unknown Wine"
        bottle = Bottle.create(
            title,
            lwin=_safe_lwin(row["lwin"]),
            varietal=row["varietal"] or "",
            country=row["country"] or "",
            source="cellardb",
            description=row["note"] or "",
            status=CellarStatus.CELLARED,
        )
        if row["vintage"]:
            try:
                bottle.vintage = int(str(row["vintage"])[:4])
            except ValueError:
                pass
        if row["price"] is not None:
            try:
                bottle.price = round(float(row["price"]), 2)
            except (TypeError, ValueError):
                pass
        prod_rows = conn.execute(
            "SELECT producers.name FROM producers "
            "JOIN bottles_producers_link ON bottles_producers_link.producer = producers.id "
            "WHERE bottles_producers_link.bottle = ?",
            (row["id"],),
        )
        pids = []
        for pr in prod_rows:
            nm = pr["name"]
            au = next((a for a in storage.list_producers() if a.name == nm), None)
            if au is None:
                au = Producer.create(nm)
                storage.upsert_producer(au)
            pids.append(au.id)
        bottle.producer_ids = pids
        tag_names = _tags_for_bottle(conn, row["id"])
        if tag_names:
            from corklog.tags_manager import TagsManager

            tm = TagsManager(storage)
            for tn in tag_names:
                tag = tm.find_or_create(tn)
                if tag.id not in bottle.tag_ids:
                    bottle.tag_ids.append(tag.id)
        storage.upsert_bottle(bottle)
        n += 1
    conn.close()
    return n


def list_cellardb_wines(library_path: Path, limit: int = 20) -> List[str]:
    db = _read_db(library_path)
    conn = sqlite3.connect(str(db))
    cur = conn.execute("SELECT wine FROM bottles LIMIT ?", (limit,))
    out = [r[0] for r in cur.fetchall()]
    conn.close()
    return out


def export_cellardb_json(storage: JsonStorage) -> str:
    rows = []
    for b in storage.list_bottles():
        rows.append({
            "wine": b.title,
            "vintage": b.vintage,
            "lwin": b.lwin,
            "producers": b.producer_ids,
        })
    return json.dumps(rows, indent=2)


def cellardb_stats(library_path: Path) -> Dict[str, int]:
    db = _read_db(library_path)
    conn = sqlite3.connect(str(db))
    bottles = conn.execute("SELECT COUNT(*) FROM bottles").fetchone()[0]
    producers = conn.execute("SELECT COUNT(*) FROM producers").fetchone()[0]
    conn.close()
    return {"bottles": bottles, "producers": producers}
