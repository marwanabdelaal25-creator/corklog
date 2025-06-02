"""Import a CellarTracker CSV export.

CellarTracker's "Export" gives a wide CSV; the columns we care about are:

    iWine, Wine, Vintage, Producer, Varietal, Country, Region,
    Quantity, Price, BeginConsume, EndConsume

``iWine`` is CellarTracker's own id (we stash it). ``BeginConsume`` /
``EndConsume`` are the drink-window years. Everything imports as *cellared*.
"""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional

from corklog.bottle import Bottle, CellarStatus
from corklog.producer import Producer
from corklog.errors import ImportError as CorklogImportError
from corklog.storage import JsonStorage


def _col(row: Dict[str, str], *names: str) -> str:
    for n in names:
        v = row.get(n)
        if v:
            return str(v).strip()
    return ""


def _int(raw: str) -> Optional[int]:
    raw = (raw or "").strip()
    return int(raw) if raw.isdigit() else None


def _parse_row(row: Dict[str, str]) -> Optional[Bottle]:
    title = _col(row, "Wine", "wine", "Name")
    if not title:
        return None
    bottle = Bottle.create(title, status=CellarStatus.CELLARED, source="cellartracker")
    bottle.vintage = _int(_col(row, "Vintage", "vintage"))
    bottle.varietal = _col(row, "Varietal", "varietal")
    bottle.country = _col(row, "Country", "country")
    price = _col(row, "Price", "price").replace("$", "")
    if price.replace(".", "", 1).isdigit():
        bottle.price = float(price)
    bottle.drink_from = _int(_col(row, "BeginConsume", "Begin"))
    bottle.drink_to = _int(_col(row, "EndConsume", "End"))
    iwine = _col(row, "iWine", "iwine")
    meta = {}
    if iwine:
        meta["iwine"] = iwine
    qty = _col(row, "Quantity", "Qty")
    if qty:
        meta["quantity"] = qty
    bottle.metadata = meta
    return bottle


def import_cellartracker(storage: JsonStorage, path: Path) -> int:
    if not path.exists():
        raise CorklogImportError("cellartracker", "missing file")
    raw = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(raw))
    n = 0
    cache: Dict[str, str] = {}
    for row in reader:
        bottle = _parse_row(row)
        if bottle is None:
            continue
        producer = _col(row, "Producer", "producer", "Winery")
        if producer:
            pid = cache.get(producer.lower())
            if not pid:
                existing = next((p for p in storage.list_producers() if p.name == producer), None)
                if existing:
                    pid = existing.id
                else:
                    pr = Producer.create(producer)
                    storage.upsert_producer(pr)
                    pid = pr.id
                cache[producer.lower()] = pid
            bottle.producer_ids = [pid]
        storage.upsert_bottle(bottle)
        n += 1
    return n


def preview(path: Path, limit: int = 5) -> List[str]:
    if not path.exists():
        return []
    reader = csv.DictReader(StringIO(path.read_text(encoding="utf-8-sig")))
    out = []
    for i, row in enumerate(reader):
        if i >= limit:
            break
        out.append("%s %s" % (_col(row, "Wine") or "?", _col(row, "Vintage") or "NV"))
    return out


def cellared_count(storage: JsonStorage) -> int:
    return sum(
        1 for b in storage.list_bottles()
        if b.source == "cellartracker" and b.status == CellarStatus.CELLARED
    )


def export_cellartracker_csv(storage: JsonStorage, dest: Path) -> int:
    fields = ["iWine", "Wine", "Vintage", "Producer", "Varietal", "Country", "Price", "BeginConsume", "EndConsume"]
    producers = {p.id: p.name for p in storage.list_producers()}
    rows = storage.list_bottles()
    with dest.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for b in rows:
            w.writerow({
                "iWine": (b.metadata or {}).get("iwine", ""),
                "Wine": b.title,
                "Vintage": b.vintage or "",
                "Producer": "; ".join(producers.get(p, p) for p in b.producer_ids),
                "Varietal": b.varietal,
                "Country": b.country,
                "Price": b.price if b.price is not None else "",
                "BeginConsume": b.drink_from or "",
                "EndConsume": b.drink_to or "",
            })
    return len(rows)
