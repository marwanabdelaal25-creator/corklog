"""JSON file storage for the whole library."""

from __future__ import annotations

import json
import os
import shutil
import threading
from copy import deepcopy
from pathlib import Path
from collections.abc import MutableMapping, Iterator
from typing import Any, Dict, List, Optional

from .producer import Producer
from .bottle import Bottle
from .collections import Collection
from .errors import NotFoundError, StorageError
from .goals import CellarGoal
from .notes import Note
from .regions import Region
from .quotes import Quote
from .vertical import Vertical
from .wishlist import Wishlist
from .tasting import Tasting
from .tag import Tag
from .rating import Rating

SCHEMA_VERSION = 2
DEFAULT_FILENAME = "library.json"

_EMPTY: Dict[str, Any] = {
    "version": SCHEMA_VERSION,
    "bottles": [],
    "producers": [],
    "wishlists": [],
    "tastings": [],
    "tags": [],
    "ratings": [],
    "goals": [],
    "quotes": [],
    "notes": [],
    "vertical": [],
    "regions": [],
    "collections": [],
    "audit": [],
    "plugins": {},
    "recurring": [],
}


class JsonStorage:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = deepcopy(_EMPTY)
        self._bottle_cache: Dict[str, Bottle] = {}

    def load(self) -> None:
        with self._lock:
            if not self.path.exists():
                self._data = deepcopy(_EMPTY)
                self._ensure_defaults()
                self._bottle_cache.clear()
                return
            try:
                raw = self.path.read_text(encoding="utf-8")
                self._data = json.loads(raw) if raw.strip() else deepcopy(_EMPTY)
            except OSError as exc:  # disk/network hiccup — be explicit
                raise StorageError("cannot read library file: %s" % exc) from exc
            except json.JSONDecodeError as exc:
                raise StorageError("corrupt JSON: {0}".format(exc)) from exc
            self._ensure_defaults()
            self._bottle_cache.clear()

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            payload = json.dumps(self._data, indent=2, ensure_ascii=False)
            try:
                tmp.write_text(payload, encoding="utf-8")
                tmp.replace(self.path)
            except OSError as exc:
                raise StorageError(f"cannot write library: {exc}") from exc

    def _ensure_defaults(self) -> None:
        for k, v in _EMPTY.items():
            self._data.setdefault(k, deepcopy(v) if isinstance(v, (dict, list)) else v)
        if not self._data.get("wishlists"):
            pass  # wishlists stay empty until user adds one
        meta = self._data.setdefault("meta", {})
        meta.setdefault("owner", "Marwan Helmy")

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return deepcopy(self._data)

    def replace_all(self, data: Dict[str, Any]) -> None:
        with self._lock:
            self._data = deepcopy(data)

    def to_dict(self) -> Dict[str, Any]:
        return self.snapshot()

    # --- bottles ---
    def list_bottles(self) -> List[Bottle]:
        out: List[Bottle] = []
        for b in self._data.get("bottles", []):
            bid = b["id"]
            if bid in self._bottle_cache:
                out.append(self._bottle_cache[bid])
            else:
                bottle = Bottle.from_dict(b)
                self._bottle_cache[bid] = bottle
                out.append(bottle)
        return out

    def get_bottle(self, bottle_id: str) -> Bottle:
        if bottle_id in self._bottle_cache:
            return self._bottle_cache[bottle_id]
        for b in self._data["bottles"]:
            if b["id"] == bottle_id:
                bottle = Bottle.from_dict(b)
                self._bottle_cache[bottle_id] = bottle
                return bottle
        raise NotFoundError("bottle", bottle_id)

    def upsert_bottle(self, bottle: Bottle) -> None:
        d = bottle.to_dict()
        for i, b in enumerate(self._data["bottles"]):
            if b["id"] == bottle.id:
                self._data["bottles"][i] = d
                self._bottle_cache[bottle.id] = bottle
                return
        self._data["bottles"].append(d)
        self._bottle_cache[bottle.id] = bottle

    def delete_bottle(self, bottle_id: str) -> None:
        before = len(self._data["bottles"])
        self._data["bottles"] = [b for b in self._data["bottles"] if b["id"] != bottle_id]
        if len(self._data["bottles"]) == before:
            raise NotFoundError("bottle", bottle_id)
        self._bottle_cache.pop(bottle_id, None)
        for sh in self.list_wishlists():
            if sh.remove_bottle(bottle_id):
                self.upsert_wishlist(sh)

    # --- producers ---
    def list_producers(self) -> List[Producer]:
        return [Producer.from_dict(a) for a in self._data.get("producers", [])]

    def get_producer(self, producer_id: str) -> Producer:
        for a in self._data["producers"]:
            if a["id"] == producer_id:
                return Producer.from_dict(a)
        raise NotFoundError("producer", producer_id)

    def upsert_producer(self, producer: Producer) -> None:
        d = producer.to_dict()
        for i, a in enumerate(self._data["producers"]):
            if a["id"] == producer.id:
                self._data["producers"][i] = d
                return
        self._data["producers"].append(d)

    # --- wishlists ---
    def list_wishlists(self) -> List[Wishlist]:
        return [Wishlist.from_dict(s) for s in self._data.get("wishlists", [])]

    def get_wishlist(self, wishlist_id: str) -> Wishlist:
        for s in self._data["wishlists"]:
            if s["id"] == wishlist_id:
                return Wishlist.from_dict(s)
        raise NotFoundError("wishlist", wishlist_id)

    def upsert_wishlist(self, wishlist: Wishlist) -> None:
        d = wishlist.to_dict()
        for i, s in enumerate(self._data["wishlists"]):
            if s["id"] == wishlist.id:
                self._data["wishlists"][i] = d
                return
        self._data["wishlists"].append(d)

    # --- tastings ---
    def list_tastings(self, bottle_id: Optional[str] = None) -> List[Tasting]:
        out = []
        for s in self._data.get("tastings", []):
            if bottle_id is None or s.get("bottle_id") == bottle_id:
                out.append(Tasting.from_dict(s))
        return out

    def add_tasting(self, tasting: Tasting) -> None:
        self._data.setdefault("tastings", []).append(tasting.to_dict())

    def upsert_tasting(self, tasting: Tasting) -> None:
        rows = self._data.setdefault("tastings", [])
        d = tasting.to_dict()
        for i, s in enumerate(rows):
            if s.get("id") == tasting.id:
                rows[i] = d
                return
        rows.append(d)

    def delete_producer(self, producer_id: str) -> None:
        before = len(self._data["producers"])
        self._data["producers"] = [a for a in self._data["producers"] if a["id"] != producer_id]
        if len(self._data["producers"]) == before:
            raise NotFoundError("producer", producer_id)

    def delete_tag(self, tag_id: str) -> None:
        before = len(self._data["tags"])
        self._data["tags"] = [t for t in self._data["tags"] if t["id"] != tag_id]
        if len(self._data["tags"]) == before:
            raise NotFoundError("tag", tag_id)

    def delete_tasting(self, tasting_id: str) -> None:
        rows = self._data.get("tastings", [])
        nxt = [s for s in rows if s.get("id") != tasting_id]
        if len(nxt) == len(rows):
            raise NotFoundError("tasting", tasting_id)
        self._data["tastings"] = nxt

    @property
    def _inner(self) -> "JsonStorage":
        return self

    @classmethod
    def open(cls, path: Path | str) -> "JsonStorage":
        st = cls(path)
        st.load()
        return st

    def _reload(self) -> None:
        self.load()

    @property
    def bottles(self) -> "_EntityDict":
        return _EntityDict(
            self.list_bottles,
            self.get_bottle,
            self.upsert_bottle,
            self.delete_bottle,
        )

    @property
    def producers(self) -> "_EntityDict":
        return _EntityDict(
            self.list_producers,
            self.get_producer,
            self.upsert_producer,
            self.delete_producer,
        )

    @property
    def tastings(self) -> "_EntityDict":
        def _get(sid: str) -> Tasting:
            for s in self.list_tastings():
                if s.id == sid:
                    return s
            raise NotFoundError("tasting", sid)

        return _EntityDict(
            self.list_tastings,
            _get,
            self.upsert_tasting,
            self.delete_tasting,
        )

    @property
    def tags(self) -> "_EntityDict":
        def _get(tid: str) -> Tag:
            for t in self.list_tags():
                if t.id == tid:
                    return t
            raise NotFoundError("tag", tid)

        return _EntityDict(
            self.list_tags,
            _get,
            self.upsert_tag,
            self.delete_tag,
        )

    # --- tags ---
    def list_tags(self) -> List[Tag]:
        return [Tag.from_dict(t) for t in self._data.get("tags", [])]

    def upsert_tag(self, tag: Tag) -> None:
        d = tag.to_dict()
        for i, t in enumerate(self._data["tags"]):
            if t["id"] == tag.id:
                self._data["tags"][i] = d
                return
        self._data["tags"].append(d)

    # --- ratings ---
    def list_ratings(self, bottle_id: Optional[str] = None) -> List[Rating]:
        rs = []
        for r in self._data.get("ratings", []):
            if bottle_id is None or r.get("bottle_id") == bottle_id:
                rs.append(Rating.from_dict(r))
        return rs

    def add_rating(self, rating: Rating) -> None:
        self._data.setdefault("ratings", []).append(rating.to_dict())
        try:
            bottle = self.get_bottle(rating.bottle_id)
            bottle.rating = rating.value
            self.upsert_bottle(bottle)
        except NotFoundError:
            pass

    # --- goals ---
    def list_goals(self) -> List[CellarGoal]:
        return [CellarGoal.from_dict(g) for g in self._data.get("goals", [])]

    def save_goals(self, goals: List[CellarGoal]) -> None:
        self._data["goals"] = [g.to_dict() for g in goals]

    # --- quotes ---
    def list_quotes(self, bottle_id: Optional[str] = None) -> List[Quote]:
        out = []
        for q in self._data.get("quotes", []):
            if bottle_id is None or q.get("bottle_id") == bottle_id:
                out.append(Quote.from_dict(q))
        return out

    def add_quote(self, quote: Quote) -> None:
        self._data.setdefault("quotes", []).append(quote.to_dict())

    # --- notes ---
    def list_notes(self, bottle_id: Optional[str] = None) -> List[Note]:
        out = []
        for n in self._data.get("notes", []):
            if bottle_id is None or n.get("bottle_id") == bottle_id:
                out.append(Note.from_dict(n))
        return out

    def add_note(self, note: Note) -> None:
        self._data.setdefault("notes", []).append(note.to_dict())
        try:
            bk = self.get_bottle(note.bottle_id)
            bk.notes_count += 1
            self.upsert_bottle(bk)
        except NotFoundError:
            pass

    # --- vertical / regions / collections ---
    def list_vertical(self) -> List[Vertical]:
        return [Vertical.from_dict(s) for s in self._data.get("vertical", [])]

    def upsert_vertical(self, vertical: Vertical) -> None:
        d = vertical.to_dict()
        for i, s in enumerate(self._data["vertical"]):
            if s["id"] == vertical.id:
                self._data["vertical"][i] = d
                return
        self._data["vertical"].append(d)

    def list_regions(self) -> List[Region]:
        return [Region.from_dict(p) for p in self._data.get("regions", [])]

    def upsert_region(self, pub: Region) -> None:
        d = pub.to_dict()
        for i, p in enumerate(self._data["regions"]):
            if p["id"] == pub.id:
                self._data["regions"][i] = d
                return
        self._data["regions"].append(d)

    def list_collections(self) -> List[Collection]:
        return [Collection.from_dict(c) for c in self._data.get("collections", [])]

    def upsert_collection(self, coll: Collection) -> None:
        d = coll.to_dict()
        for i, c in enumerate(self._data["collections"]):
            if c["id"] == coll.id:
                self._data["collections"][i] = d
                return
        self._data["collections"].append(d)

    def raw_get(self, key: str) -> Any:
        return self._data.get(key)

    def raw_set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def snapshot_dir(self, dest: Path) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save()
        shutil.copy2(self.path, dest / self.path.name)

    def bulk_upsert_bottles(self, bottles: List[Bottle]) -> int:
        n = 0
        for b in bottles:
            self.upsert_bottle(b)
            n += 1
        return n

    def count_entities(self) -> Dict[str, int]:
        return {
            "bottles": len(self._data.get("bottles", [])),
            "producers": len(self._data.get("producers", [])),
            "tastings": len(self._data.get("tastings", [])),
            "tags": len(self._data.get("tags", [])),
            "quotes": len(self._data.get("quotes", [])),
            "notes": len(self._data.get("notes", [])),
        }

    @property
    def version(self) -> int:
        return int(self._data.get("version", SCHEMA_VERSION))

    @property
    def meta(self) -> Dict[str, Any]:
        return self._data.setdefault("meta", {})


def default_storage_path() -> Path:
    home = Path(os.path.expanduser("~"))
    env = os.environ.get("CORKLOG_HOME")
    if env:
        return Path(env) / DEFAULT_FILENAME
    return home / ".corklog" / DEFAULT_FILENAME


def open_storage(path: Optional[str] = None) -> JsonStorage:
    p = Path(path) if path else default_storage_path()
    st = JsonStorage(p)
    st.load()
    return st


# alias some callers expect
LibraryStore = JsonStorage
open_library = open_storage


class _EntityDict(MutableMapping):
    """Mutable dict view over JSON-backed entities."""

    def __init__(self, list_fn, get_fn, upsert_fn, delete_fn) -> None:
        self._list_fn = list_fn
        self._get_fn = get_fn
        self._upsert_fn = upsert_fn
        self._delete_fn = delete_fn

    def _map(self) -> Dict[str, Any]:
        return {item.id: item for item in self._list_fn()}

    def __getitem__(self, key: str):
        return self._get_fn(key)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        try:
            self._get_fn(key)
            return True
        except NotFoundError:
            return False

    def __setitem__(self, key: str, value) -> None:
        self._upsert_fn(value)

    def __delitem__(self, key: str) -> None:
        self._delete_fn(key)

    def __iter__(self):
        return iter(self._map())

    def __len__(self) -> int:
        return len(self._map())

    def values(self):
        return self._map().values()


class LibraryFacade:
    """High-level API wrapping JsonStorage — used by scripts and tests."""

    def __init__(self, path: Optional[str] = None):
        self._st = open_storage(path)

    @property
    def storage(self) -> JsonStorage:
        return self._st

    def save(self) -> None:
        self._st.save()

    def reload(self) -> None:
        self._st.load()

    def add_bottle(self, title: str, **kwargs) -> Bottle:
        bottle = Bottle.create(title, **kwargs)
        self._st.upsert_bottle(bottle)
        return bottle

    def log_tasting(self, bottle_id: str, ml_end: int, score: float | None = None) -> Tasting:
        bottle = self._st.get_bottle(bottle_id)
        sess = Tasting.create(
            bottle_id=bottle.id,
            ml_start=bottle.ml_poured,
            ml_end=ml_end,
            score=score,
        )
        self._st.add_tasting(sess)
        bottle.ml_poured = ml_end
        self._st.upsert_bottle(bottle)
        return sess

    def stats_text(self) -> str:
        from corklog.stats import format_stats

        return format_stats(self._st)

    def streak_text(self) -> str:
        from corklog.streaks import streak_summary

        return streak_summary(self._st)

    def backup(self, dest: Optional[Path] = None) -> Path:
        from corklog.backup import create_backup

        return create_backup(self._st, dest)

    def path(self) -> Path:
        return self._st.path

    def entity_summary(self) -> Dict[str, int]:
        return self._st.count_entities()

    def find_bottle(self, query: str) -> Optional[Bottle]:
        from corklog.search import SearchEngine

        hits = SearchEngine(self._st).search_bottles(query, limit=1)
        if not hits:
            return None
        return self._st.get_bottle(hits[0].id)

    def mark_drunk(self, bottle_id: str) -> Bottle:
        bottle = self._st.get_bottle(bottle_id)
        bottle.mark_finished()
        self._st.upsert_bottle(bottle)
        return bottle

    def list_open(self) -> List[Bottle]:
        from corklog.bottle import CellarStatus

        return [b for b in self._st.list_bottles() if b.status == CellarStatus.OPEN]

    def import_csv(self, path: Path) -> int:
        from corklog.io_csv import import_csv

        return import_csv(self._st, path)

    def export_csv(self, path: Path) -> int:
        from corklog.io_csv import export_csv

        return export_csv(self._st, path)
