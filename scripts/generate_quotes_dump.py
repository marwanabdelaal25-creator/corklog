#!/usr/bin/env python3
"""Generate historical tasting-note / quote data for corklog tests."""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "quotes"

# (slug, producer, flagship vintage) — wines people keep notes on.
WINES = [
    ("chateau-margaux", "Château Margaux", 2015),
    ("penfolds-grange", "Penfolds", 2016),
    ("domaine-leflaive-montrachet", "Domaine Leflaive", 2014),
    ("sassicaia", "Tenuta San Guido", 2019),
    ("vega-sicilia-unico", "Vega Sicilia", 2010),
    ("krug-grande-cuvee", "Krug", 2012),
    ("ridge-monte-bello", "Ridge Vineyards", 2018),
    ("guigal-la-mouline", "E. Guigal", 2017),
]
DESCRIPTORS = ["tar", "rose petal", "black cherry", "cassis", "graphite", "leather",
               "tobacco leaf", "violet", "crushed stone", "brioche", "candied citrus",
               "forest floor", "white pepper", "dried fig", "wet slate", "truffle"]
STRUCTURE = ["firm tannins", "racy acidity", "long finish", "silky texture",
             "grippy backbone", "saline lift", "creamy mousse", "fine bead"]


def _note(rng: random.Random) -> str:
    nose = ", ".join(rng.sample(DESCRIPTORS, rng.randint(2, 4)))
    palate = rng.choice(STRUCTURE)
    return "Nose of %s; %s. %s." % (nose, palate, rng.choice(
        ["Needs another five years", "Drinking beautifully now", "Decant for an hour",
         "Past its best", "Will reward patience"]))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(4242)
    corpus = []
    for slug, producer, vintage in WINES:
        for occasion in ("dinner", "blind tasting", "cellar check"):
            for i in range(rng.randint(120, 200)):
                corpus.append({
                    "bottle_id": slug,
                    "producer": producer,
                    "vintage": vintage,
                    "occasion": occasion,
                    "quote_id": f"{slug}-{occasion.replace(' ', '-')}-{i:04d}",
                    "text": _note(rng),
                    "score": round(rng.uniform(85, 100), 0),
                    "decant_minutes": rng.choice([0, 30, 60, 90, 120]),
                    "tags": rng.sample(DESCRIPTORS, rng.randint(0, 3)),
                })

    by_year = {}
    for y in range(2018, 2026):
        by_year[str(y)] = {
            "notes_added": rng.randint(40, 400),
            "top_wines": [w[0] for w in rng.sample(WINES, k=4)],
            "sample": [_note(rng) for _ in range(rng.randint(30, 60))],
        }

    master = {"schema": 1, "notes": corpus, "by_year": by_year, "cross_refs": []}
    for i, q in enumerate(corpus[::17]):
        master["cross_refs"].append(
            {"from": q["quote_id"], "to": corpus[(i * 31) % len(corpus)]["quote_id"], "relation": "same-flight"}
        )

    p = OUT / "quotes_master.json"
    p.write_text(json.dumps(master, indent=2, ensure_ascii=False), encoding="utf-8")

    shard_size = 2500
    for idx in range(0, len(corpus), shard_size):
        shard = corpus[idx: idx + shard_size]
        sp = OUT / f"quotes_shard_{idx // shard_size:03d}.json"
        sp.write_text(json.dumps(shard, indent=2, ensure_ascii=False), encoding="utf-8")

    total = sum(f.stat().st_size for f in OUT.glob("*.json"))
    print(f"tasting-notes dump: {len(corpus)} notes, {total / (1024 * 1024):.2f} MB -> {OUT}")


if __name__ == "__main__":
    main()
