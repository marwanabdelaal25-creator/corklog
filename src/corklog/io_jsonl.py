"""JSON Lines import/export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from corklog.bottle import Bottle
from corklog.tasting import Tasting
from corklog.errors import ExportError, ImportError as CorklogImportError
from corklog.storage import JsonStorage


def export_jsonl_bottles(storage: JsonStorage, dest: Path) -> int:
    bottles = storage.list_bottles()
    try:
        with dest.open("w", encoding="utf-8") as fh:
            for bottle in bottles:
                fh.write(json.dumps(bottle.to_dict(), ensure_ascii=False) + "\n")
        return len(bottles)
    except OSError as exc:
        raise ExportError("jsonl", str(exc)) from exc


def export_jsonl_tastings(storage: JsonStorage, dest: Path) -> int:
    tastings = storage.list_tastings()
    with dest.open("w", encoding="utf-8") as fh:
        for sess in tastings:
            fh.write(json.dumps(sess.to_dict(), ensure_ascii=False) + "\n")
    return len(tastings)


def export_full_library(storage: JsonStorage, dest: Path) -> int:
    """One JSON object per line with entity type prefix."""
    n = 0
    with dest.open("w", encoding="utf-8") as fh:
        for bottle in storage.list_bottles():
            fh.write(json.dumps({"_type": "bottle", **bottle.to_dict()}, ensure_ascii=False) + "\n")
            n += 1
        for producer in storage.list_producers():
            fh.write(json.dumps({"_type": "producer", **producer.to_dict()}, ensure_ascii=False) + "\n")
            n += 1
        for sess in storage.list_tastings():
            fh.write(json.dumps({"_type": "tasting", **sess.to_dict()}, ensure_ascii=False) + "\n")
            n += 1
    return n


def import_jsonl_bottles(storage: JsonStorage, src: Path) -> int:
    if not src.exists():
        raise CorklogImportError("jsonl", "missing %s" % src)
    n = 0
    for line in _iter_lines(src):
        data = json.loads(line)
        if data.get("_type") and data["_type"] != "bottle":
            continue
        data.pop("_type", None)
        bottle = Bottle.from_dict(data)
        storage.upsert_bottle(bottle)
        n += 1
    return n


def import_jsonl_tastings(storage: JsonStorage, src: Path) -> int:
    n = 0
    for line in _iter_lines(src):
        data = json.loads(line)
        if data.get("_type") and data["_type"] != "tasting":
            continue
        data.pop("_type", None)
        sess = Tasting.from_dict(data)
        storage.add_tasting(sess)
        n += 1
    return n


def import_mixed_jsonl(storage: JsonStorage, src: Path) -> Dict[str, int]:
    counts = {"bottle": 0, "producer": 0, "tasting": 0, "skipped": 0}
    for line in _iter_lines(src):
        data = json.loads(line)
        kind = data.pop("_type", "bottle")
        if kind == "bottle":
            storage.upsert_bottle(Bottle.from_dict(data))
            counts["bottle"] += 1
        elif kind == "producer":
            from corklog.producer import Producer

            storage.upsert_producer(Producer.from_dict(data))
            counts["producer"] += 1
        elif kind == "tasting":
            storage.add_tasting(Tasting.from_dict(data))
            counts["tasting"] += 1
        else:
            counts["skipped"] += 1
    return counts


def _iter_lines(path: Path) -> Iterable[str]:
    with path.open(encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                yield ln


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in _iter_lines(path))
