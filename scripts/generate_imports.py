#!/usr/bin/env python3
"""Generate multi-source import fixtures for corklog (stdlib only).

One sub-folder per service, with per-month chunks across several years plus a
quarterly rollup. Each service uses roughly the shape of its real export so the
importers (and a curious human) see something believable.
"""
from __future__ import annotations

import csv
import json
import random
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "imports"

SOURCES = ["cellartracker", "vivino", "winesearcher", "cellardb", "decanter", "wineapp"]
YEARS = list(range(2019, 2026))
VARIETALS = ["Cabernet Sauvignon", "Merlot", "Pinot Noir", "Chardonnay", "Syrah",
             "Nebbiolo", "Sangiovese", "Tempranillo", "Riesling", "Grenache"]
REGIONS = {"Bordeaux": "France", "Burgundy": "France", "Tuscany": "Italy",
           "Rioja": "Spain", "Napa Valley": "USA", "Barossa Valley": "Australia",
           "Mosel": "Germany", "Douro": "Portugal", "Mendoza": "Argentina"}
PRODUCERS = ["Château Lestage", "Domaine Roulot", "Tenuta San Guido", "Bodega Muga",
             "Ridge Vineyards", "Penfolds", "Dr. Loosen", "Quinta do Noval", "Catena Zapata"]


def _lwin(rng: random.Random) -> str:
    return "%07d" % rng.randint(1000000, 9999999)


def _rows(rng: random.Random, n: int) -> list[dict]:
    rows = []
    for i in range(n):
        region = rng.choice(list(REGIONS))
        producer = rng.choice(PRODUCERS)
        vintage = rng.randint(1990, 2022)
        rows.append({
            "wine": "%s %s" % (producer, rng.choice(VARIETALS)),
            "producer": producer,
            "vintage": vintage,
            "varietal": rng.choice(VARIETALS),
            "region": region,
            "country": REGIONS[region],
            "lwin": _lwin(rng),
            "price": round(rng.uniform(12, 600), 2),
            "rating": round(rng.uniform(3.0, 5.0), 1),
            "quantity": rng.randint(1, 12),
            "drink_from": vintage + rng.randint(2, 6),
            "drink_to": vintage + rng.randint(8, 30),
            "scan_date": date(rng.randint(2019, 2025), rng.randint(1, 12), rng.randint(1, 28)).isoformat(),
        })
    return rows


def _write_cellartracker(path: Path, rows: list[dict]) -> None:
    fields = ["iWine", "Wine", "Vintage", "Producer", "Varietal", "Country",
              "Region", "Quantity", "Price", "BeginConsume", "EndConsume"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({
                "iWine": r["lwin"], "Wine": r["wine"], "Vintage": r["vintage"],
                "Producer": r["producer"], "Varietal": r["varietal"], "Country": r["country"],
                "Region": r["region"], "Quantity": r["quantity"], "Price": r["price"],
                "BeginConsume": r["drink_from"], "EndConsume": r["drink_to"],
            })


def _write_vivino(path: Path, rows: list[dict]) -> None:
    fields = ["Winery", "Wine name", "Vintage", "Region", "Country", "Your rating", "Scan date"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({
                "Winery": r["producer"], "Wine name": r["varietal"], "Vintage": r["vintage"],
                "Region": r["region"], "Country": r["country"],
                "Your rating": r["rating"], "Scan date": r["scan_date"],
            })


def _write_winesearcher_json(path: Path, rows: list[dict]) -> None:
    payload = {
        "page": 1,
        "wines": [
            {
                "lwin": r["lwin"], "name": r["wine"], "vintage": r["vintage"],
                "region": r["region"], "country": r["country"],
                "price": r["price"], "currency": "USD", "score": round(r["rating"] * 20, 0),
            }
            for r in rows
        ],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_generic_json(path: Path, source: str, rows: list[dict]) -> None:
    path.write_text(
        json.dumps({"source": source, "version": 2, "bottles": rows}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for source in SOURCES:
        src_dir = OUT / source
        src_dir.mkdir(parents=True, exist_ok=True)
        for year in YEARS:
            year_dir = src_dir / str(year)
            year_dir.mkdir(exist_ok=True)
            for month in range(1, 13):
                rng = random.Random(hash((source, year, month)) & 0xFFFFFFFF)
                rows = _rows(rng, rng.randint(8, 22))
                stem = f"{source}_{year}_{month:02d}"
                if source == "cellartracker":
                    p = year_dir / f"{stem}.csv"
                    _write_cellartracker(p, rows)
                elif source == "vivino":
                    p = year_dir / f"{stem}.csv"
                    _write_vivino(p, rows)
                elif source == "winesearcher":
                    p = year_dir / f"{stem}.json"
                    _write_winesearcher_json(p, rows)
                else:
                    p = year_dir / f"{stem}.json"
                    _write_generic_json(p, source, rows)
                total += p.stat().st_size

            for q in range(1, 5):
                rng = random.Random(hash((source, year, q, "q")) & 0xFFFFFFFF)
                rows = _rows(rng, rng.randint(40, 70))
                p = year_dir / f"{source}_{year}_Q{q}.json"
                _write_generic_json(p, source, rows)
                total += p.stat().st_size

    print(f"import fixtures: {len(SOURCES)} sources, {len(YEARS)} years -> {total / (1024 * 1024):.2f} MB")


if __name__ == "__main__":
    main()
