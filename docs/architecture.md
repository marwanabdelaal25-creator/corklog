# Architecture

A tour of how corklog is put together and why. Nothing here is clever; it's a
CLI over a JSON file. The goal was "easy to reason about at midnight", not
"scales to a million users".

## The shape of it

```
cli ──> storage (JsonStorage) ──> library.json
 │            │
 │            ├── migrate          (schema v0 → v1 → v2 on load)
 │            └── models           (Bottle, Producer, Tasting, ...)
 │
 ├── search / stats / reports / streaks / goals   (read the store, compute things)
 ├── io_* codecs                                  (import / export)
 └── server                                       (read-only HTTP, stdlib only)
```

## Module map

**Core models** — plain dataclasses, no storage dependency:

- `bottle` — the `Bottle` entity + `CellarStatus` + a `BottleCatalog` query
  helper. This is where the drink-window logic lives (`is_ready`,
  `drink_window_status`, `years_to_window`).
- `producer`, `region`, `vertical`, `wishlist` — the things bottles hang off.
- `tasting` — one pour from a bottle: `ml_start`/`ml_end` and an optional score.
- `rating`, `quotes`, `note`, `tag`, `collections`, `goals` — the trimmings.

**Storage**

- `storage` — `JsonStorage`: load/save (atomic temp-file + rename), per-entity
  CRUD, and a small `LibraryFacade` for scripts.
- `migrate` — forward-only schema migrations keyed off the `version` field.

**Parsing & validation**

- `parser` — dates, durations, `0/750` style pour progress, key=value pairs.
- `validators` — field-level checks shared across the model layer.
- `lwin` — LWIN parsing/validation (7/11/16/18 digits) plus the base-7 root and
  the embedded vintage.

**Business logic**

- `search` — fuzzy-ish search across bottles, producers, notes and quotes.
- `stats` — pour pace, value by region/varietal, vintage-decade distribution,
  ready-to-drink counts, completion rate.
- `reports` — the human-readable text views the CLI prints, including the
  "what to open tonight" picker.
- `streaks`, `goals`, `recurring` — habit-tracking bits.
- `audit_log`, `backup`, `plugins` — operational odds and ends.

**I/O codecs** — each import source in its own module:

- `io_csv`, `io_jsonl` — the generic in/out formats.
- `io_cellartracker`, `io_vivino`, `io_winesearcher`, `io_cellardb` — service-specific imports.

**Surface**

- `cli` — argparse subcommands wiring everything together.
- `server` — a stdlib `http.server` handler for LAN browsing.

## Why JSON, not SQLite

I went back and forth. SQLite would give me indexes and real queries for free.
But:

- I open `library.json` in an editor more often than I'd like to admit, to fix
  a producer's name or paste in a volume_ml I looked up. You can't do that with a
  binary `.db` without a tool.
- `grep` and `jq` are my query engine. "Which 2023 bottles did I rate 5?" is a
  one-liner against text.
- The whole library is a few MB even after years. Loading it all into memory is
  fine; I'm not Netflix.

The cost is that every write rewrites the file. I make that safe with an atomic
write (temp file + `os.replace`) so a crash can't leave a half-written library.

## Things I'd do differently

- `ml_poured` / `ml_remaining` model a bottle as a single vessel you drain. It
  doesn't cope with "I have six of these" — quantity lives in metadata on
  import, not as a first-class field. One day.
- The plugin registry is more scaffolding than feature — I've written exactly
  one plugin and it lives in my dotfiles.
