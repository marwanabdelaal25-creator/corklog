"""CSV import and export for corklog cellars."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path
from typing import Dict, List, Optional

from corklog.bottle import Bottle, CellarStatus
from corklog.producer import Producer
from corklog.errors import ExportError, ImportError as CorklogImportError
from corklog.parser import split_csv_line
from corklog.storage import JsonStorage

CSV_FIELDS = ["title", "producer", "lwin", "vintage", "region", "varietal", "price", "status", "rating", "tags"]
IMPORT_STATUS = {
    "want": CellarStatus.WANT,
    "wishlist": CellarStatus.WANT,
    "cellared": CellarStatus.CELLARED,
    "owned": CellarStatus.CELLARED,
    "open": CellarStatus.OPEN,
    "drunk": CellarStatus.DRUNK,
    "dumped": CellarStatus.DUMPED,
}


def _parse_status(raw: Optional[str]) -> CellarStatus:
    if not raw:
        return CellarStatus.CELLARED
    return IMPORT_STATUS.get(raw.strip().lower(), CellarStatus.CELLARED)


def export_csv(storage: JsonStorage, dest: Path) -> int:
    try:
        with dest.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
            w.writeheader()
            n = 0
            producers = {a.id: a.name for a in storage.list_producers()}
            tags = {t.id: t.name for t in storage.list_tags()}
            regions = {r.id: r.name for r in storage.list_regions()}
            for b in storage.list_bottles():
                prod = "; ".join(producers.get(pid, pid) for pid in b.producer_ids)
                tg = ", ".join(tags.get(t, t) for t in b.tag_ids)
                w.writerow({
                    "title": b.title,
                    "producer": prod,
                    "lwin": b.lwin or "",
                    "vintage": b.vintage or "",
                    "region": regions.get(b.region_id, "") if b.region_id else "",
                    "varietal": b.varietal,
                    "price": b.price if b.price is not None else "",
                    "status": b.status.value,
                    "rating": b.rating_value if b.rating_value is not None else "",
                    "tags": tg,
                })
                n += 1
        return n
    except OSError as exc:
        raise ExportError("csv", str(exc)) from exc


def import_csv(storage: JsonStorage, src: Path, update: bool = False) -> int:
    if not src.exists():
        raise CorklogImportError("csv", "file not found")
    text = src.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    count = 0
    for row in reader:
        title = (row.get("title") or "").strip()
        if not title:
            continue
        lwin = (row.get("lwin") or "").strip() or None
        existing = None
        if update and lwin:
            existing = next((b for b in storage.list_bottles() if b.lwin == lwin), None)
        if existing:
            bottle = existing
            bottle.title = title
            bottle.status = _parse_status(row.get("status"))
        else:
            bottle = Bottle.create(
                title,
                lwin=lwin,
                status=_parse_status(row.get("status")),
                source="csv",
            )
        vintage = row.get("vintage")
        if vintage and str(vintage).strip().isdigit():
            bottle.vintage = int(vintage)
        if row.get("varietal"):
            bottle.varietal = row["varietal"].strip()
        if row.get("country"):
            bottle.country = row["country"].strip()
        price = row.get("price")
        if price and str(price).replace(".", "", 1).isdigit():
            bottle.price = float(price)
        rt = row.get("rating")
        if rt and str(rt).replace(".", "", 1).isdigit():
            bottle.rating = float(rt)
        producer = (row.get("producer") or "").strip()
        if producer:
            for part in producer.split(";"):
                nm = part.strip()
                if not nm:
                    continue
                au = next((a for a in storage.list_producers() if a.name == nm), None)
                if au is None:
                    au = Producer.create(nm)
                    storage.upsert_producer(au)
                if au.id not in bottle.producer_ids:
                    bottle.producer_ids.append(au.id)
        storage.upsert_bottle(bottle)
        count += 1
    return count


def parse_row(line: str) -> Dict[str, str]:
    parts = split_csv_line(line)
    return dict(zip(CSV_FIELDS, parts + [""] * (len(CSV_FIELDS) - len(parts))))


def validate_csv_headers(path: Path) -> List[str]:
    if not path.exists():
        return CSV_FIELDS
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    headers = reader.fieldnames or []
    required = ["title"]
    return [h for h in required if h not in headers]


def sample_rows(path: Path, n: int = 3) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    out = []
    for i, row in enumerate(reader):
        if i >= n:
            break
        out.append(dict(row))
    return out
