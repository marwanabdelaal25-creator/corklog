"""Search bottles, producers, notes, and quotes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Pattern

from corklog.producer import Producer
from corklog.bottle import Bottle
from corklog.notes import Note
from corklog.quotes import Quote
from corklog.storage import JsonStorage


@dataclass
class SearchHit:
    kind: str
    id: str
    title: str
    score: float
    snippet: str = ""


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().strip())


# FIXME: tune threshold — 0.15 feels arbitrary in practice

def _score(query: str, text: str) -> float:
    q = _norm(query)
    t = _norm(text)
    if not q or not t:
        return 0.0
    if q == t:
        return 1.0
    if q in t:
        return 0.8 + 0.2 * (len(q) / len(t))
    qt = set(q.split())
    tt = set(t.split())
    if not qt:
        return 0.0
    overlap = len(qt & tt) / len(qt)
    return overlap * 0.6


class SearchEngine:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def search_bottles(self, query: str, limit: int = 20) -> List[SearchHit]:
        if not query or not query.strip():
            return []
        hits: List[SearchHit] = []
        for bottle in self.storage.list_bottles():
            sc = _score(query, bottle.title)
            if bottle.lwin and query.replace("-", "") in (bottle.lwin or ""):
                sc = max(sc, 0.9)
            if sc > 0.15:
                hits.append(
                    SearchHit("bottle", bottle.id, bottle.title, sc, bottle.status.value)
                )
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:limit]

    def search_producers(self, query: str, limit: int = 10) -> List[SearchHit]:
        out = []
        for a in self.storage.list_producers():
            sc = _score(query, a.name)
            if sc > 0.2:
                out.append(SearchHit("producer", a.id, a.name, sc))
        out.sort(key=lambda h: h.score, reverse=True)
        return out[:limit]

    def search_notes(self, query: str, limit: int = 15) -> List[SearchHit]:
        out = []
        for n in self.storage.list_notes():
            sc = max(_score(query, n.body), _score(query, n.title))
            if sc > 0.2:
                out.append(SearchHit("note", n.id, n.title or n.excerpt(40), sc, n.excerpt(80)))
        out.sort(key=lambda h: h.score, reverse=True)
        return out[:limit]

    def search_quotes(self, query: str, limit: int = 15) -> List[SearchHit]:
        out = []
        for q in self.storage.list_quotes():
            sc = _score(query, q.text)
            if sc > 0.2:
                out.append(SearchHit("quote", q.id, q.preview(50), sc, q.preview(100)))
        out.sort(key=lambda h: h.score, reverse=True)
        return out[:limit]

    def search_all(self, query: str) -> List[SearchHit]:
        hits = self.search_bottles(query, limit=30)
        hits.extend(self.search_producers(query, limit=10))
        hits.extend(self.search_notes(query, limit=10))
        hits.extend(self.search_quotes(query, limit=10))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits

    def filter_bottles(
        self,
        status: Optional[str] = None,
        tag_id: Optional[str] = None,
        wishlist_id: Optional[str] = None,
    ) -> List[Bottle]:
        bottles = self.storage.list_bottles()
        if status:
            bottles = [b for b in bottles if b.status.value == status]
        if tag_id:
            bottles = [b for b in bottles if tag_id in b.tag_ids]
        if wishlist_id:
            bottles = [b for b in bottles if wishlist_id in b.wishlist_ids]
        return bottles

    def advanced(self, expr: str) -> List[Bottle]:
        """Tiny DSL: status:cellared tag:bordeaux title:margaux lwin:1011266"""
        tokens = expr.split()
        pool = list(self.storage.list_bottles())
        tag_by_name = {t.name.lower(): t.id for t in self.storage.list_tags()}
        for tok in tokens:
            if ":" not in tok:
                q = _norm(tok)
                pool = [b for b in pool if _score(q, b.title) > 0.15 or b.matches(tok)]
                continue
            key, val = tok.split(":", 1)
            key, val = key.lower(), val.lower()
            if key == "status":
                pool = [b for b in pool if b.status.value == val]
            elif key == "tag":
                tid = tag_by_name.get(val)
                if tid:
                    pool = [b for b in pool if tid in b.tag_ids]
            elif key == "title":
                pool = [b for b in pool if val in b.title.lower()]
            elif key == "lwin":
                pool = [b for b in pool if b.lwin and val in b.lwin]
        return sorted(pool, key=lambda b: b.title.lower())

    def regex_filter(self, pattern: str, field: str = "title") -> List[Bottle]:
        pat: Pattern[str] = re.compile(pattern, re.IGNORECASE)
        res = []
        for b in self.storage.list_bottles():
            val = getattr(b, field, "") or ""
            if pat.search(str(val)):
                res.append(b)
        return res

    def highlight(self, text: str, query: str) -> str:
        if not query:
            return text
        pat = re.compile(re.escape(query), re.I)
        return pat.sub(lambda m: "**%s**" % m.group(0), text)

    def suggest(self, prefix: str, limit: int = 8) -> List[str]:
        """Title prefix suggestions for interactive CLI."""
        p = prefix.lower()
        titles = sorted({b.title for b in self.storage.list_bottles()})
        out = [t for t in titles if t.lower().startswith(p)]
        if len(out) < limit:
            out.extend([t for t in titles if p in t.lower() and t not in out][: limit - len(out)])
        return out[:limit]

    def recent_bottles(self, days: int = 90) -> List[Bottle]:
        from datetime import date, timedelta

        cutoff = date.today() - timedelta(days=days)
        out = []
        for b in self.storage.list_bottles():
            if b.started_at:
                try:
                    if date.fromisoformat(b.started_at[:10]) >= cutoff:
                        out.append(b)
                except ValueError:
                    pass
        return sorted(out, key=lambda b: b.started_at or "", reverse=True)
