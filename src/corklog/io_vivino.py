"""Import a Vivino CSV export.

Vivino's data export is a per-scan list of wines you rated:

    Winery, Wine name, Vintage, Region, Country, Your rating, Scan date

A row with a rating is something you've actually drunk and scored, so it lands
as *drunk*; a bare row (wishlist export) lands as *want*. Vivino rates 1-5,
which is already our scale.
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


def _rating(row: Dict[str, str]) -> Optional[float]:
    raw = _col(row, "Your rating", "your_rating", "Rating")
    if not raw:
        return None
    try:
        val = float(raw)
    except ValueError:
        return None
    return min(5.0, val) if val > 0 else None


def _parse_row(row: Dict[str, str]) -> Optional[Bottle]:
    title = _col(row, "Wine name", "Wine", "name")
    if not title:
        return None
    rating = _rating(row)
    status = CellarStatus.DRUNK if rating is not None else CellarStatus.WANT
    bottle = Bottle.create(title, status=status, source="vivino")
    yr = _col(row, "Vintage", "vintage")
    if yr[:4].isdigit():
        bottle.vintage = int(yr[:4])
    bottle.country = _col(row, "Country", "country")
    if rating is not None:
        bottle.rating = rating
    scanned = _col(row, "Scan date", "scan_date", "Date")
    if status == CellarStatus.DRUNK and scanned:
        bottle.finished_at = scanned[:10]
    region = _col(row, "Region", "region")
    if region:
        bottle.metadata = {"region": region}
    return bottle


def import_vivino(storage: JsonStorage, path: Path) -> int:
    if not path.exists():
        raise CorklogImportError("vivino", "file not found")
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    n = 0
    cache: Dict[str, str] = {}
    for row in reader:
        bottle = _parse_row(row)
        if bottle is None:
            continue
        winery = _col(row, "Winery", "winery", "Producer")
        if winery:
            pid = cache.get(winery.lower())
            if not pid:
                existing = next((p for p in storage.list_producers() if p.name == winery), None)
                pid = existing.id if existing else None
                if pid is None:
                    pr = Producer.create(winery)
                    storage.upsert_producer(pr)
                    pid = pr.id
                cache[winery.lower()] = pid
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
        out.append("%s — %s" % (_col(row, "Wine name") or "?", _col(row, "Winery") or "?"))
    return out


def scanned(storage: JsonStorage) -> List[Bottle]:
    return [b for b in storage.list_bottles() if b.source == "vivino"]


def history_summary(storage: JsonStorage) -> str:
    rows = scanned(storage)
    if not rows:
        return "No Vivino scans imported."
    lines = ["Vivino scans (%d):" % len(rows)]
    for b in rows[:20]:
        lines.append("  - %s (%s)" % (b.title[:45], b.vintage or "NV"))
    return "\n".join(lines)
