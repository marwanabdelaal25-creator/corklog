# corklog

A wine-cellar and tasting-notes tracker I built because CellarTracker kept
nudging me toward a Pro subscription, Vivino's app changes its layout every few
months, and the spreadsheet I'd kept since 2019 had sprouted four tabs and a
column of `=IF(...)` formulas only I understood.

Everything lives in one JSON file (`library.json`) on disk. Add the bottles you
own, when they hit their drink window, what you paid, where they sit in the
rack, and what they tasted like — then `grep` for "Barolo" at midnight without a
login or an internet connection.

```bash
pip install .
corklog init ~/cellar/library.json
corklog bottle-add "Château Margaux" --producer "Château Margaux" \
    --vintage 2015 --varietal "Cabernet Sauvignon" --country France \
    --price 650 --drink-from 2030 --drink-to 2055 --lwin 1011266
corklog tasting-log <bottle-id> --pour 150 --score 4.5 --occasion "Sunday roast"
corklog rate <bottle-id> 4.5 --note "Tight but profound; give it a decade"
corklog stats
```

## What it does

- Track bottles with **producer, region, country, varietal, vintage, bottle
  size, price and a drink window** (`drink_from`–`drink_to`), plus a cellar
  status: `want` (wishlist) → `cellared` → `open` → `drunk` / `dumped`.
- **Drink windows are the whole point.** `corklog` knows whether a bottle is
  *too young*, *ready*, or *past peak* for any given year, surfaces what's ready
  to open tonight, and warns you about the bottles fading at the back of the
  rack (`corklog report` / the `drink_tonight` picker).
- Log **tastings** — a pour from a bottle, with the amount, a 0–5 score, the
  occasion and who you shared it with. A 750 ml bottle drunk over three nights
  is three tastings against one bottle.
- **Score** wines on a 0–5 half-star scale, keep short reviews, and pull a
  leaderboard or a score-by-decade chart.
- **Cellar analytics**: total value of what's in the rack, value and counts by
  region / varietal / vintage decade / producer, ready-to-drink counts, and how
  much (in litres) you actually drank this year.
- Wishlists, verticals (the same label across vintages), tags, and memorable
  tasting quotes.
- Yearly goals ("24 bottles in 2026"), tasting streaks, and an LWIN
  (Liv-ex Wine Identification Number) for every bottle that has one.
- Import from a **CellarTracker** export, a **Vivino** ratings dump, a generic
  CSV, a local sqlite **cellar.db**, or a **Wine-Searcher** lookup by LWIN.
- A tiny stdlib-only HTTP server so the kitchen tablet can browse the cellar on
  the LAN.

## What it doesn't do

- Sell you wine, or tell you where to buy it. Use Wine-Searcher.
- Sync live with CellarTracker/Vivino — export a file and import it. Live sync
  needs OAuth trust I don't extend to a weekend project.
- Score wines *for* you, or recommend "because you liked". I have a wine shop
  for that.
- Multi-user accounts. This is my cellar, not a marketplace.

## Drink windows

Every bottle can carry a `drink_from` / `drink_to` pair of years. From those,
`corklog` computes:

- `is_ready(year)` — is it in the window?
- `drink_window_status(year)` — `too young` / `ready` / `past peak` / `unknown`
- `years_to_window(year)` — how many years until it's ready

`corklog report` leans on these to tell you what to pull from the rack tonight,
sorted so nothing dies of old age before you get to it.

## Storage

One JSON document, pretty-printed, written atomically (temp file + rename, so a
crash mid-save can't shred the cellar). I picked JSON over SQLite on purpose: I
wanted to open the file, read it, and fix a typo by hand. The schema is
versioned and migrates forward automatically — see
[`docs/architecture.md`](docs/architecture.md) and
[`docs/formats.md`](docs/formats.md).

## Importing

```bash
corklog import cellar_export.csv --format cellartracker
corklog import vivino_ratings.csv --format vivino
corklog import bottles.csv --format csv
corklog import ~/CellarApp --format cellardb     # reads CellarApp/cellar.db
corklog fetch-lwin 1011266                        # pull price/region from Wine-Searcher
```

See [`docs/recipes.md`](docs/recipes.md) for end-to-end workflows and
[`docs/faq.md`](docs/faq.md) for the questions people actually ask me.

## Author

Marwan Helmy — marwanabdelaal25@gmail.com

MIT licensed. Personal project, started summer 2024.
