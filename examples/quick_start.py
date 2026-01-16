#!/usr/bin/env python3
"""30-second smoke test: build a tiny cellar, log a tasting, print it back."""
from __future__ import annotations

import tempfile
from pathlib import Path

from corklog.producer import Producer
from corklog.bottle import Bottle, CellarStatus
from corklog.rating import Rating
from corklog.storage import JsonStorage
from corklog.tasting import Tasting


def main() -> None:
    path = Path(tempfile.mkdtemp()) / "library.json"
    store = JsonStorage(path)
    store.load()

    penfolds = Producer.create("Penfolds")
    store.upsert_producer(penfolds)

    grange = Bottle.create(
        "Penfolds Grange",
        lwin="1011266",
        vintage=2016,
        varietal="Shiraz",
        country="Australia",
        price=900.0,
        drink_from=2026,
        drink_to=2046,
        status=CellarStatus.OPEN,
    )
    grange.producer_ids = [penfolds.id]
    store.upsert_bottle(grange)

    # pour a 150 ml glass and score it
    store.add_tasting(
        Tasting.create(
            grange.id,
            ml_start=0,
            ml_end=150,
            score=4.5,
            occasion="Sunday roast",
            started_at="2026-03-01T20:00:00",
        )
    )
    grange.ml_poured = 150
    store.upsert_bottle(grange)
    store.add_rating(Rating.create(grange.id, value=4.5, review="Tar and dark fruit; still primary."))
    store.save()

    print("saved cellar to", store.path)
    for bottle in store.list_bottles():
        print(" ", bottle.summary_line())


if __name__ == "__main__":
    main()
