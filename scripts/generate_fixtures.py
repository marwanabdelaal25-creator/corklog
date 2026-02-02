#!/usr/bin/env python3
"""Generate large corklog cellar JSON fixtures (stdlib only)."""
from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "libraries"

VARIETALS = [
    "Cabernet Sauvignon", "Merlot", "Pinot Noir", "Chardonnay", "Sauvignon Blanc",
    "Syrah", "Nebbiolo", "Sangiovese", "Tempranillo", "Riesling", "Grenache",
    "Malbec", "Chenin Blanc", "Zinfandel", "Gewürztraminer", "Nerello Mascalese",
]
STYLES = ["red", "white", "rose", "sparkling", "dessert", "fortified", "orange"]
REGIONS = {
    "Bordeaux": "France", "Burgundy": "France", "Champagne": "France",
    "Northern Rhône": "France", "Loire Valley": "France", "Tuscany": "Italy",
    "Piedmont": "Italy", "Rioja": "Spain", "Priorat": "Spain", "Napa Valley": "USA",
    "Willamette Valley": "USA", "Barossa Valley": "Australia", "Mosel": "Germany",
    "Marlborough": "New Zealand", "Douro": "Portugal", "Mendoza": "Argentina",
}
CUVEES = ["Grand Vin", "Reserva", "Gran Reserva", "Estate", "Vieilles Vignes",
          "Riserva", "Brut", "Premier Cru", "Grand Cru", "Single Vineyard", "Old Vine"]
PRODUCER_STEMS = ["Château", "Domaine", "Bodega", "Weingut", "Tenuta", "Quinta", "Cantina"]
PERSONAS = [
    "bordeaux_collector", "burgundy_purist", "champagne_lover", "natural_wine_fan",
    "new_world_explorer", "everyday_drinker", "cellar_investor", "sommelier",
    "fortified_collector", "rhone_ranger",
]
STATUSES = ["want", "cellared", "open", "drunk", "dumped"]
DESCRIPTORS = ["tar", "rose", "cassis", "graphite", "leather", "cherry", "tobacco",
               "violet", "citrus", "flint", "honey", "brioche", "earth", "spice"]


def _producer(rng: random.Random) -> str:
    return "%s %s" % (rng.choice(PRODUCER_STEMS),
                      "".join(rng.choice("aeilornst") for _ in range(rng.randint(4, 8))).capitalize())


def _wine_name(rng: random.Random, producer: str) -> str:
    if rng.random() < 0.5:
        return "%s %s" % (producer, rng.choice(CUVEES))
    return "%s %s" % (producer, rng.choice(VARIETALS))


def _lwin(rng: random.Random) -> str:
    base = "%07d" % rng.randint(1000000, 9999999)
    return base + ("%04d" % rng.randint(1980, 2024) if rng.random() < 0.5 else "")


def _bottle_entry(rng: random.Random, idx: int, year: int) -> dict:
    vintage = rng.randint(1985, year)
    producer = _producer(rng)
    region = rng.choice(list(REGIONS))
    status = rng.choice(STATUSES)
    drink_from = vintage + rng.randint(2, 8)
    drink_to = drink_from + rng.randint(5, 25)
    drunk_on = None
    if status in ("drunk", "dumped"):
        drunk_on = date(min(year, drink_to), rng.randint(1, 12), rng.randint(1, 28)).isoformat()
    return {
        "id": "wn-%d-%06d" % (year, idx),
        "title": _wine_name(rng, producer),
        "producers": [producer],
        "lwin": _lwin(rng),
        "varietal": rng.choice(VARIETALS),
        "style": rng.choice(STYLES),
        "region": region,
        "country": REGIONS[region],
        "vintage": vintage,
        "volume_ml": rng.choice([375, 750, 750, 750, 1500]),
        "price": round(rng.uniform(8, 950), 2),
        "drink_from": drink_from,
        "drink_to": drink_to,
        "cellar_location": "%s%d-%d" % (rng.choice("ABCDEF"), rng.randint(1, 12), rng.randint(1, 24)),
        "drunk_on": drunk_on,
        "rating": round(rng.uniform(2.5, 5.0), 1) if rng.random() > 0.2 else None,
        "status": status,
        "notes": ", ".join(rng.sample(DESCRIPTORS, rng.randint(0, 4))),
        "tags": ["tag-%d" % rng.randint(1, 120) for _ in range(rng.randint(0, 4))],
    }


def _library_blob(rng: random.Random, *, entries: int, label: str) -> dict:
    year = int(label.split("-")[-1]) if label[-4:].isdigit() else 2025
    bottles = [_bottle_entry(rng, i, year - rng.randint(0, 3)) for i in range(entries)]
    return {
        "schema": 3,
        "label": label,
        "persona": rng.choice(PERSONAS),
        "generated": True,
        "stats": {
            "count": len(bottles),
            "cellar_value": round(sum(b["price"] for b in bottles
                                      if b["status"] in ("cellared", "open")), 2),
            "drunk": sum(1 for b in bottles if b["status"] == "drunk"),
        },
        "bottles": bottles,
        "wishlists": {
            "to-buy": [b["id"] for b in bottles if b["status"] == "want"][:80],
            "cellar": [b["id"] for b in bottles if b["status"] == "cellared"][:120],
        },
    }


def _write_json(path: Path, data: dict) -> int:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0

    for i, entries in enumerate((4200, 5100, 3800), start=1):
        rng = random.Random(1000 + i)
        data = _library_blob(rng, entries=entries, label=f"megacellar-{i}")
        n = _write_json(OUT / f"megacellar-{i}.json", data)
        total += n
        print(f"megacellar-{i}.json: {n / (1024 * 1024):.2f} MB")

    for year in range(2018, 2026):
        rng = random.Random(year)
        snap = {
            "year": year,
            "bottles": [_bottle_entry(rng, j, year) for j in range(rng.randint(120, 220))],
        }
        total += _write_json(OUT / f"snapshot-{year}.json", snap)

    for persona in PERSONAS:
        rng = random.Random(hash(persona) & 0xFFFFFFFF)
        data = _library_blob(rng, entries=rng.randint(180, 350), label=f"persona-{persona}")
        total += _write_json(OUT / f"persona-{persona}.json", data)

    print(f"cellar fixtures total: {total / (1024 * 1024):.2f} MB raw -> {OUT}")


if __name__ == "__main__":
    main()
