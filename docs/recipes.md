# Recipes

Copy-pasteable workflows. All of these assume `corklog init` has run and
`$CORKLOG_HOME` points at where you keep `library.json` (defaults to
`~/.corklog/`).

## Add a bottle to the cellar

```bash
corklog bottle-add "Barolo Brunate" --producer "Giuseppe Rinaldi" \
    --vintage 2018 --varietal Nebbiolo --country Italy --price 180 \
    --drink-from 2028 --drink-to 2048
```

## Open one and log the pour

```bash
corklog tasting-log <bottle-id> --pour 150 --score 4.5 --occasion "Tuesday"
corklog rate <bottle-id> 4.5 --note "Tar and roses; still tight"
corklog bottle-show <bottle-id>      # status + drink window
```

A 750 ml bottle drunk over three nights is three `tasting-log` calls; once it's
empty corklog flips it to `drunk` for you.

## What should I open tonight?

```bash
corklog report tonight    # cellared bottles that are ready, soonest-to-fade first
corklog stats             # ready-to-drink count, cellar value, by-status
```

## Move your CellarTracker cellar in

1. CellarTracker → Account → Export → "Download your data".
2. You'll get a CSV with `iWine,Wine,Vintage,Producer,Varietal,…`.

```bash
corklog import cellar_export.csv --format cellartracker
```

## Pull in Vivino ratings

```bash
corklog import vivino_ratings.csv --format vivino
```

## Look up price and region for a bottle

```bash
export WINESEARCHER_API_KEY=...
corklog fetch-lwin 1011266
```

## What did I drink this year?

```bash
corklog report year --year 2025
corklog stats
```

## Find a bottle

```bash
corklog bottle-list -q "barolo"
corklog search "nebbiolo"
corklog search --expr "^Penfolds"
```

## Back up before you do something dumb

```bash
corklog backup --dir ~/backups
```

## Grep, because you can

```bash
jq '.bottles[] | select(.vintage==2016 and .rating==5) | .title' ~/.corklog/library.json
grep -i "margaux" ~/.corklog/library.json
```
