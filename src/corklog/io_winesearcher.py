"""Wine-Searcher lookups — resolve an LWIN to a wine + current market price.

Thin wrapper over a Wine-Searcher-style JSON API. The one call I actually use is
:func:`bottle_from_lwin` — paste an LWIN, get a populated ``Bottle`` (name,
vintage, region, average price) back. Set the key in ``$WINESEARCHER_API_KEY``.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any, List, Optional

from corklog.bottle import Bottle, CellarStatus
from corklog.errors import ImportError as CorklogImportError
from corklog.lwin import validate_lwin, normalize_lwin
from corklog.storage import JsonStorage

BASE = "https://api.wine-searcher.com/v1"


def _key(explicit: Optional[str] = None) -> str:
    return explicit or os.environ.get("WINESEARCHER_API_KEY", "") or "demo"


def _get(path: str, params: dict, timeout: int = 10) -> dict[str, Any]:
    url = "%s%s?%s" % (BASE, path, urllib.parse.urlencode(params))
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except OSError as exc:
        raise CorklogImportError("winesearcher", str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise CorklogImportError("winesearcher", "bad json") from exc


def fetch_by_lwin(lwin: str, api_key: Optional[str] = None) -> dict[str, Any]:
    if not validate_lwin(lwin):
        raise CorklogImportError("winesearcher", "bad LWIN: %s" % lwin)
    return _get("/wine", {"lwin": normalize_lwin(lwin), "api_key": _key(api_key)})


def _first(data: dict[str, Any]) -> Optional[dict[str, Any]]:
    for key in ("wines", "matches", "results"):
        rows = data.get(key)
        if rows:
            return rows[0]
    return None


def _apply(bottle: Bottle, w: dict[str, Any]) -> None:
    if w.get("vintage") and str(w["vintage"])[:4].isdigit():
        bottle.vintage = int(str(w["vintage"])[:4])
    if w.get("region"):
        bottle.metadata = dict(bottle.metadata or {}, region=str(w["region"]))
    if w.get("country"):
        bottle.country = str(w["country"])
    if w.get("price"):
        try:
            bottle.price = round(float(w["price"]), 2)
        except (TypeError, ValueError):
            pass
    if w.get("currency"):
        bottle.currency = str(w["currency"])
    if w.get("description") or w.get("note"):
        bottle.description = str(w.get("description") or w.get("note"))


def bottle_from_lwin(lwin: str, api_key: Optional[str] = None) -> Bottle:
    data = fetch_by_lwin(lwin, api_key)
    w = _first(data)
    if w is None:
        raise CorklogImportError("winesearcher", "no match for %s" % lwin)
    name = w.get("name") or w.get("wine") or "Unknown Wine"
    bottle = Bottle.create(name, lwin=normalize_lwin(lwin), source="winesearcher",
                           status=CellarStatus.WANT)
    _apply(bottle, w)
    return bottle


def search(query: str, api_key: Optional[str] = None, limit: int = 5) -> List[dict[str, Any]]:
    try:
        data = _get("/search", {"q": query, "api_key": _key(api_key)})
    except CorklogImportError:
        return []
    return (data.get("results") or data.get("wines") or [])[:limit]


def enrich_bottle(storage: JsonStorage, bottle_id: str, api_key: Optional[str] = None) -> Bottle:
    bottle = storage.get_bottle(bottle_id)
    if not bottle.lwin:
        raise CorklogImportError("winesearcher", "bottle has no LWIN")
    w = _first(fetch_by_lwin(bottle.lwin, api_key))
    if w:
        _apply(bottle, w)
    storage.upsert_bottle(bottle)
    return bottle


def bulk_enrich(storage: JsonStorage, limit: int = 10, api_key: Optional[str] = None) -> int:
    n = 0
    for bottle in storage.list_bottles():
        if not bottle.lwin:
            continue
        try:
            enrich_bottle(storage, bottle.id, api_key)
            n += 1
        except CorklogImportError:
            continue
        if n >= limit:
            break
    return n


def format_search_hit(w: dict[str, Any]) -> str:
    name = w.get("name") or w.get("wine") or "Unknown"
    vintage = w.get("vintage") or "NV"
    price = (" — %s" % w.get("price")) if w.get("price") else ""
    return "%s %s%s" % (name, vintage, price)
