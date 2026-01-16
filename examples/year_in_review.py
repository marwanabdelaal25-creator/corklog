#!/usr/bin/env python3
"""Build a small 2025 drinking history and print the year-in-review summary."""
from __future__ import annotations

import tempfile
from pathlib import Path

from corklog.bottle import Bottle, CellarStatus
from corklog.reports import ReportBuilder
from corklog.storage import JsonStorage

DRUNK = [
    ("Rioja Gran Reserva", 2015, "Tempranillo", 55.0, 4.0, "2025-01-15"),
    ("Chablis Premier Cru", 2021, "Chardonnay", 60.0, 4.5, "2025-02-20"),
    ("Barolo Brunate", 2016, "Nebbiolo", 80.0, 5.0, "2025-03-11"),
    ("Côte-Rôtie", 2018, "Syrah", 120.0, 4.5, "2025-04-02"),
]


def main() -> None:
    store = JsonStorage(Path(tempfile.mkdtemp()) / "library.json")
    store.load()
    for title, vintage, varietal, price, score, drunk_on in DRUNK:
        bottle = Bottle.create(
            title, vintage=vintage, varietal=varietal, price=price, status=CellarStatus.DRUNK
        )
        bottle.ml_poured = bottle.volume_ml
        bottle.finished_at = drunk_on
        bottle.rating = score
        store.upsert_bottle(bottle)
    store.save()

    print(ReportBuilder(store).yearly_summary(2025))


if __name__ == "__main__":
    main()
