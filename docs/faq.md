# FAQ

Questions friends actually ask when I show them this.

### Why not just use CellarTracker?

I do, kind of — I export from it. But I wanted my cellar in a file I own, that
works on a plane, and that won't grow a paywall around the stats I care about.
corklog is the local copy I trust.

### I own six of the same wine — does it handle that?

Not as a first-class field. A bottle is one record; if you buy a case, the
quantity rides along in `metadata` on import (CellarTracker exports it). I drink
one record down via tastings and add another when I open the next. If you need
real inventory counts, this isn't a cellar-management ERP.

### How are scores stored — stars or numbers?

A float 0–5, half-steps allowed; the display uses ★ and ½. Vivino already uses a
1–5 scale so it maps straight across; CellarTracker's drink-window dates become
`drink_from`/`drink_to`.

### What's a drink window?

The pair of years (`drink_from`, `drink_to`) a wine is worth opening in. corklog
turns that into `too young` / `ready` / `past peak` for any year, counts how
many bottles are ready right now, and — the bit I actually use —
`corklog report tonight` lists what to pull from the rack, soonest-to-fade
first.

### What's the difference between `volume_ml` and a tasting's pour?

`volume_ml` is the bottle size (750 by default). A tasting's `ml_end - ml_start`
is the size of that pour. `ml_poured / volume_ml` is how empty the bottle is;
when it hits 100% the bottle is `drunk`.

### Can I edit the JSON by hand?

Yes, that's half the point. Keep it valid JSON — the app re-reads it on the next
command, and the migrator tidies/upgrades the shape if needed.

### Will it sync to my other laptop?

Put `library.json` in Dropbox/Syncthing and point both machines at it (or set
`CORKLOG_HOME`). There's no conflict resolution beyond "last writer wins", so
don't run both at once.

### Why is there a tiny web server in here?

So the tablet in the kitchen can browse the cellar on the LAN (`corklog serve`).
It's read-only and stdlib-only — no Flask, no npm.

### What about a corked or disappointing bottle?

Set it `dumped`. It still counts in your history (and your dumped-rate stat), it
just won't show up as ready to drink.

### Is my data sent anywhere?

Only if you run `fetch-lwin`, which calls Wine-Searcher. Everything else is
local. No telemetry, no accounts.

### Why "corklog"?

Cork + log. Also every good wine name on PyPI was taken. I'm not precious about
it.
