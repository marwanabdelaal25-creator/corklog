# Changelog

All notable changes to corklog. Dates are when I actually cut the tag, not when
I meant to.

## 1.2.0
- Tasting streaks + a per-weekday pour breakdown, and cellar valuation by region
  and varietal.
- `vertical` progress reports (the next vintage to open in a vertical).
- Drink-window analytics: ready-to-drink counts and the "what to open tonight"
  picker.
- Schema bumped to v2 (see Migrations).

## 1.0.0
- First version I'd call usable. Stable JSON schema, CSV import/export, the
  CellarTracker and Vivino importers, scores with reviews, and the stats page.

## 0.8.0
- Wine-Searcher lookup by LWIN (`fetch-lwin`).
- sqlite `cellar.db` import.
- Tasting-note quotes with descriptors and a decant time.

## 0.6.0
- Wishlists and tags.
- Yearly goals + the goals manager.

## 0.4.0
- Tastings (per-pour logging) and the reports builder.

## 0.3.0
- Schema v1: split the flat bottle blob into bottles + producers + tastings.

## 0.1.0
- First commit. A `Bottle` dataclass, a JSON store, and `bottle-add`.

## Migrations

The on-disk schema version lives in the top-level `version` key. `corklog`
migrates forward automatically on load; there is no downgrade.

- **0 → 1**: legacy `to-drink` / `owned` status strings folded into `want` /
  `cellared`; introduced the `producers`, `verticals` and `tastings`
  collections.
- **1 → 2**: scores normalised to a single float (older builds stored a nested
  `{value, score}` object); `volume_ml` promoted out of `metadata`.
