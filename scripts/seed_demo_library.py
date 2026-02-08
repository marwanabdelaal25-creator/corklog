#!/usr/bin/env python3
"""Seed a small demo cellar + a curated sample_library.json via the real API.

Building these through ``JsonStorage`` (rather than hand-writing JSON) keeps the
fixtures honest: whatever schema the app saves today is exactly what lands on
disk here.
"""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from pathlib import Path

from corklog.producer import Producer
from corklog.bottle import Bottle, CellarStatus
from corklog.goals import CellarGoal
from corklog.rating import Rating
from corklog.storage import JsonStorage
from corklog.tag import Tag
from corklog.tasting import Tasting

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"
DEMO = FIX / "demo"

# (wine, producer, lwin, vintage, varietal, country, price, drink_from, drink_to, rating, status)
CURATED = [
    ("Château Margaux", "Château Margaux", "1011266", 2015, "Cabernet Sauvignon", "France", 650.0, 2030, 2055, 5.0, "cellared"),
    ("Penfolds Grange", "Penfolds", "2033444", 2016, "Shiraz", "Australia", 900.0, 2026, 2046, 4.5, "open"),
    ("Sassicaia", "Tenuta San Guido", "1099880", 2019, "Cabernet Sauvignon", "Italy", 280.0, 2027, 2045, None, "cellared"),
    ("Rioja Gran Reserva", "Bodega Muga", None, 2015, "Tempranillo", "Spain", 55.0, 2023, 2035, 4.0, "drunk"),
    ("Chablis Premier Cru", "Domaine Roulot", None, 2021, "Chardonnay", "France", 60.0, 2024, 2030, 4.0, "drunk"),
    ("Barolo Brunate", "Giuseppe Rinaldi", None, 2018, "Nebbiolo", "Italy", 180.0, 2028, 2048, None, "cellared"),
    ("Cloudy Bay Sauvignon Blanc", "Cloudy Bay", None, 2022, "Sauvignon Blanc", "New Zealand", 30.0, 2023, 2026, 3.5, "drunk"),
    ("Krug Grande Cuvée", "Krug", None, 2012, "Chardonnay", "France", 200.0, 2022, 2040, None, "want"),
]


def _build_sample() -> None:
    path = FIX / "sample_library.json"
    if path.exists():
        path.unlink()
    st = JsonStorage(path)
    st.load()
    producers: dict[str, str] = {}
    tag_first = Tag.create("first-growth", id="tag-first", color="#7b1e3a")
    tag_value = Tag.create("everyday", id="tag-value", color="#2d6a4f")
    st.upsert_tag(tag_first)
    st.upsert_tag(tag_value)
    for i, row in enumerate(CURATED):
        title, producer, lwin, vintage, varietal, country, price, df, dt, rating, status = row
        if producer not in producers:
            p = Producer.create(producer, id=f"prod-{i:02d}")
            st.upsert_producer(p)
            producers[producer] = p.id
        bottle = Bottle.create(
            title, id=f"bottle-{i:02d}", lwin=lwin, vintage=vintage, varietal=varietal,
            country=country, price=price, drink_from=df, drink_to=dt,
            status=CellarStatus(status),
        )
        bottle.producer_ids = [producers[producer]]
        bottle.tag_ids = ["tag-first" if price >= 150 else "tag-value"]
        bottle.cellar_location = "%s%d-%d" % ("ABCDEF"[i % 6], (i % 4) + 1, i + 1)
        if status == "drunk":
            bottle.ml_poured = bottle.volume_ml
            bottle.finished_at = f"{min(vintage + 5, 2025)}-06-15"
        st.upsert_bottle(bottle)
        if rating is not None:
            st.add_rating(Rating.create(bottle.id, value=rating, review=""))
    # one open bottle with a logged pour (Grange)
    st.add_tasting(
        Tasting.create("bottle-01", ml_start=0, ml_end=200, score=4.5,
                       occasion="Sunday roast", started_at="2025-03-15T20:00:00")
    )
    st.save_goals([CellarGoal.create("Drink 24 in 2026", "bottles", 24, "year")])
    st.save()


def _build_demo() -> None:
    DEMO.mkdir(parents=True, exist_ok=True)
    rng = random.Random(7)
    today = date.today()
    path = DEMO / "demo_library.json"
    if path.exists():
        path.unlink()
    st = JsonStorage(path)
    st.load()
    producer = Producer.create("Demo Estate", id="demo-prod")
    st.upsert_producer(producer)
    varietals = ["Cabernet Sauvignon", "Pinot Noir", "Chardonnay", "Syrah", "Riesling"]
    for i in range(48):
        acquired = today - timedelta(days=rng.randint(30, 1800))
        vintage = rng.randint(1995, 2022)
        status = rng.choice(["cellared", "open", "drunk", "want"])
        bottle = Bottle.create(
            f"Demo Cuvée {i}", id=f"demo-{i:03d}", vintage=vintage,
            varietal=rng.choice(varietals), country="France",
            price=round(rng.uniform(15, 400), 2),
            drink_from=vintage + rng.randint(2, 6), drink_to=vintage + rng.randint(8, 25),
            status=CellarStatus(status),
        )
        bottle.producer_ids = [producer.id]
        if status == "drunk":
            bottle.ml_poured = bottle.volume_ml
            bottle.finished_at = (acquired + timedelta(days=rng.randint(30, 400))).isoformat()
            st.upsert_bottle(bottle)
            st.add_rating(Rating.create(bottle.id, value=float(rng.randint(3, 5))))
        else:
            st.upsert_bottle(bottle)
    st.save()

    stats = {
        "generated_on": today.isoformat(),
        "bottles_per_month": [rng.randint(0, 8) for _ in range(24)],
        "by_style": {"red": 24, "white": 12, "sparkling": 6, "dessert": 3, "fortified": 3},
        "by_region": {"Bordeaux": 9, "Burgundy": 7, "Tuscany": 6, "Napa Valley": 5, "Rioja": 4},
    }
    (DEMO / "demo_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")


def main() -> None:
    FIX.mkdir(parents=True, exist_ok=True)
    _build_sample()
    _build_demo()
    print(f"seeded sample_library.json + demo fixtures under {FIX}")


if __name__ == "__main__":
    main()
