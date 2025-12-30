# Formats

## The library file

One JSON object, schema `version: 2`. The top-level keys are collections:

```json
{
  "version": 2,
  "bottles": [ ... ],
  "producers": [ ... ],
  "tastings": [ ... ],
  "wishlists": [ ... ],
  "verticals": [ ... ],
  "regions": [ ... ],
  "tags": [ ... ],
  "ratings": [ ... ],
  "quotes": [ ... ],
  "notes": [ ... ],
  "goals": [ ... ],
  "collections": [ ... ],
  "recurring": [],
  "audit": [],
  "plugins": {},
  "meta": { "owner": "Marwan Helmy" }
}
```

### A bottle record

```json
{
  "id": "wn-7c1a2b3c4d5e",
  "title": "Château Margaux",
  "producer_ids": ["prod-00"],
  "lwin": "1011266",
  "region_id": null,
  "vertical_id": null,
  "vertical_index": null,
  "vintage": 2015,
  "varietal": "Cabernet Sauvignon",
  "country": "France",
  "volume_ml": 750,
  "ml_poured": 0,
  "price": 650.0,
  "currency": "USD",
  "drink_from": 2030,
  "drink_to": 2055,
  "cellar_location": "A3-12",
  "kind": "red",
  "format": "750ml",
  "status": "cellared",
  "acquired_at": null,
  "started_at": null,
  "finished_at": null,
  "tag_ids": ["tag-first"],
  "wishlist_ids": [],
  "label_url": "",
  "rating": null
}
```

- `volume_ml` is the bottle size; `ml_poured` is how much you've drunk (equal to
  `volume_ml` once the bottle is `drunk`).
- `lwin` accepts a 7, 11, 16 or 18-digit LWIN (Liv-ex Wine Identification
  Number), ignoring spaces and dashes.
- `kind` is `red` / `white` / `rose` / `sparkling` / `fortified` / `dessert`;
  `format` is the bottle size (`750ml`, `magnum`, …).
- `drink_from` / `drink_to` are the years that bound the drink window.
- `status` is `want` → `cellared` → `open` → `drunk` / `dumped`.

### A tasting record

```json
{
  "id": "…",
  "bottle_id": "wn-…",
  "started_at": "2026-03-15T20:00:00",
  "ml_start": 0,
  "ml_end": 150,
  "score": 4.5,
  "occasion": "Sunday roast",
  "with_whom": "Sara",
  "notes": "Tar and roses; still primary."
}
```

`ml_end - ml_start` is the size of the pour. Several tastings against one bottle
add up as you work through it; when `ml_poured` reaches `volume_ml` the bottle
is `drunk`.

## Import formats

| `--format`      | Source                        | Shape |
|-----------------|-------------------------------|-------|
| `cellartracker` | CellarTracker account export  | CSV: `iWine,Wine,Vintage,Producer,Varietal,Country,Region,Quantity,Price,BeginConsume,EndConsume` |
| `vivino`        | Vivino ratings export         | CSV: `Winery,Wine name,Vintage,Region,Country,Your rating,Scan date` |
| `csv`           | corklog's own export          | CSV: `title,producer,lwin,vintage,region,varietal,price,status,rating,tags` |
| `cellardb`      | local sqlite cellar app       | reads `cellar.db` (bottles / producers / notes tables) |

CellarTracker rows import as `cellared`, with `BeginConsume`/`EndConsume`
becoming the drink window. A Vivino row with a rating imports as `drunk` (Vivino
already uses a 1–5 scale); a bare row imports as `want`.

## Wine-Searcher lookup

`corklog fetch-lwin 1011266` hits `api.wine-searcher.com` (set
`WINESEARCHER_API_KEY`), resolves the LWIN to a wine record, and pulls the name,
vintage, region, country and average market price.
