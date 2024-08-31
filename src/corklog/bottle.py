"""Bottle entity — one wine in the cellar (a specific label + vintage)."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from enum import Enum
from typing import Any, List, Optional
import uuid

from corklog.validators import (
    require_non_empty,
    validate_lwin,
    validate_volume,
    validate_year,
    validate_progress,
    validate_rating_value,
)
from corklog.rating import Rating

# a 750ml bottle ≈ 5 standard pours
STANDARD_BOTTLE_ML = 750


class CellarStatus(str, Enum):
    WANT = "want"          # on the wishlist, not bought yet
    CELLARED = "cellared"  # owned, unopened, resting
    OPEN = "open"          # opened, being drunk
    DRUNK = "drunk"        # finished
    DUMPED = "dumped"      # corked / poured down the sink

    def __str__(self) -> str:
        return self.value


@dataclass
class Bottle:
    title: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    producer_ids: list[str] = field(default_factory=list)
    lwin: str | None = None
    region_id: str | None = None
    vertical_id: str | None = None
    vertical_index: float | None = None
    vintage: int | None = None
    varietal: str = ""
    country: str = ""
    volume_ml: int = STANDARD_BOTTLE_ML
    ml_poured: int = 0
    price: float | None = None
    currency: str = "USD"
    drink_from: int | None = None
    drink_to: int | None = None
    cellar_location: str = ""
    kind: str = "red"          # red | white | rose | sparkling | fortified | dessert
    format: str = "750ml"      # bottle size
    status: CellarStatus = CellarStatus.CELLARED
    acquired_at: str | None = None
    started_at: str | None = None   # opened on
    finished_at: str | None = None  # emptied on
    tag_ids: list[str] = field(default_factory=list)
    wishlist_ids: list[str] = field(default_factory=list)
    label_url: str = ""
    description: str = ""
    source: str = "manual"
    notes_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    _rating_obj: Rating | None = field(default=None, repr=False, compare=False)
    _rating_val: float | None = field(default=None, repr=False, compare=False)

    @classmethod
    def create(cls, title: str, **kwargs: Any) -> "Bottle":
        kw = dict(kwargs)
        if "status" in kw and not isinstance(kw["status"], CellarStatus):
            kw["status"] = CellarStatus(str(kw["status"]))
        if "year" in kw:  # people say "year", the cellar calls it vintage
            kw["vintage"] = kw.pop("year")
        bid = kw.pop("id", None) or uuid.uuid4().hex[:12]
        return cls(title=title, id=bid, **kw)

    @classmethod
    def quick(cls, title: str, **kwargs: Any) -> "Bottle":
        return cls.create(title, **kwargs)

    def __post_init__(self) -> None:
        self.title = require_non_empty(self.title, "title")
        self.lwin = validate_lwin(self.lwin)
        if self.vintage is not None:
            self.vintage = validate_year(self.vintage)
        if self.volume_ml is not None:
            validate_volume(self.ml_poured, self.volume_ml)
        if self.price is not None:
            self.price = round(float(self.price), 2)
        if isinstance(self.status, str):
            self.status = CellarStatus(self.status)

    # people say "year"; internally it's the vintage
    @property
    def year(self) -> int | None:
        return self.vintage

    @year.setter
    def year(self, val: int | None) -> None:
        self.vintage = validate_year(val) if val is not None else None

    @property
    def rating(self) -> Rating | None:
        if self._rating_obj is not None:
            return self._rating_obj
        if self._rating_val is not None:
            return Rating.create(self.id, value=self._rating_val)
        return None

    @rating.setter
    def rating(self, val: Rating | float | int | None) -> None:
        self._rating_obj = None
        self._rating_val = None
        if val is None:
            return
        if isinstance(val, Rating):
            self._rating_obj = val
        else:
            self._rating_val = validate_rating_value(float(val))

    @property
    def rating_value(self) -> float | None:
        if self._rating_obj is not None:
            return self._rating_obj.value
        return self._rating_val

    @rating_value.setter
    def rating_value(self, val: float | int | None) -> None:
        self.rating = val

    def progress_pct(self) -> float:
        """How empty the bottle is (0 = full, 100 = gone)."""
        if not self.volume_ml:
            return 0.0
        pct = 100.0 * self.ml_poured / self.volume_ml
        return validate_progress(min(100.0, pct))

    @property
    def progress(self) -> float:
        return self.progress_pct()

    def set_volume(self, current: int, total: int | None = None) -> None:
        if total is not None:
            self.volume_ml = total
        validate_volume(current, self.volume_ml)
        self.ml_poured = current

    # --- drink window ---
    def is_ready(self, when: int | date | None = None) -> bool:
        yr = self._as_year(when)
        if self.drink_from is None and self.drink_to is None:
            return True
        lo = self.drink_from if self.drink_from is not None else yr
        hi = self.drink_to if self.drink_to is not None else yr
        return lo <= yr <= hi

    def drink_window_status(self, when: int | date | None = None) -> str:
        yr = self._as_year(when)
        if self.drink_from is None and self.drink_to is None:
            return "unknown"
        if self.drink_from is not None and yr < self.drink_from:
            return "too young"
        if self.drink_to is not None and yr > self.drink_to:
            return "past peak"
        return "ready"

    def years_to_window(self, when: int | date | None = None) -> Optional[int]:
        yr = self._as_year(when)
        if self.drink_from is not None and yr < self.drink_from:
            return self.drink_from - yr
        return 0 if self.is_ready(yr) else None

    @staticmethod
    def _as_year(when: int | date | None) -> int:
        if when is None:
            return date.today().year
        if isinstance(when, date):
            return when.year
        return int(when)

    # --- status transitions ---
    def cellar(self, when: date | None = None) -> None:
        self.status = CellarStatus.CELLARED
        self.acquired_at = (when or date.today()).isoformat()

    def mark_open(self, when: date | None = None) -> None:
        self.status = CellarStatus.OPEN
        self.started_at = (when or date.today()).isoformat()

    def mark_finished(self, when: date | None = None) -> None:
        self.status = CellarStatus.DRUNK
        self.finished_at = (when or date.today()).isoformat()
        if self.volume_ml:
            self.ml_poured = self.volume_ml

    def mark_drunk(self, when: date | None = None) -> None:
        self.mark_finished(when)

    def set_status(self, status: CellarStatus | str) -> None:
        self.status = CellarStatus(status) if isinstance(status, str) else status

    def dump(self, when: date | None = None) -> None:
        self.status = CellarStatus.DUMPED
        self.finished_at = (when or date.today()).isoformat()

    def short_label(self) -> str:
        yr = (" %d" % self.vintage) if self.vintage else " NV"
        return "{title}{yr}".format(title=self.title[:60], yr=yr)

    def summary_line(self) -> str:
        return "{label} | {st} | {win}".format(
            label=self.short_label(),
            st=self.status.value,
            win=self.drink_window_status(),
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for k in ("_rating_obj", "_rating_val"):
            d.pop(k, None)
        d["status"] = self.status.value
        if self._rating_obj is not None:
            d["rating"] = self._rating_obj.to_dict()
        elif self._rating_val is not None:
            d["rating"] = self._rating_val
        else:
            d["rating"] = None
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Bottle":
        kw: dict[str, Any] = {}
        fields = cls.__dataclass_fields__
        for key, val in data.items():
            if key == "rating":
                continue
            if key in fields:
                kw[key] = val
        if "status" in kw and not isinstance(kw["status"], CellarStatus):
            kw["status"] = CellarStatus(str(kw["status"]))
        rating_raw = data.get("rating")
        b = cls(**{k: kw[k] for k in kw if k in fields})
        if isinstance(rating_raw, dict):
            b._rating_obj = Rating.from_dict(rating_raw)
        elif rating_raw is not None:
            b._rating_val = validate_rating_value(float(rating_raw))
        return b

    def matches(self, query: str) -> bool:
        q = query.lower()
        if q in self.title.lower():
            return True
        if self.varietal and q in self.varietal.lower():
            return True
        if self.lwin and q in self.lwin:
            return True
        return False

    def matches_query(self, query: str) -> bool:
        q = query.lower()
        for hay in (self.title, self.varietal, self.country, self.description):
            if hay and q in hay.lower():
                return True
        if self.lwin and q in self.lwin:
            return True
        return False

    def is_active(self) -> bool:
        return self.status in (CellarStatus.OPEN, CellarStatus.CELLARED)

    def days_open(self) -> Optional[int]:
        if not self.started_at:
            return None
        start = date.fromisoformat(self.started_at[:10])
        end = date.today()
        if self.finished_at:
            end = date.fromisoformat(self.finished_at[:10])
        return max(0, (end - start).days)

    def ml_remaining(self) -> Optional[int]:
        if self.volume_ml is None:
            return None
        return max(0, self.volume_ml - self.ml_poured)

    def glasses_left(self, pour_ml: int = 150) -> int:
        rem = self.ml_remaining() or 0
        return rem // max(1, pour_ml)


class BottleCatalog:
    """Query helpers over a bottle list — no storage dependency."""

    def __init__(self, bottles: List[Bottle]):
        self.bottles = bottles

    def by_status(self, status: CellarStatus | str) -> List[Bottle]:
        st = CellarStatus(status) if isinstance(status, str) else status
        return [b for b in self.bottles if b.status == st]

    def by_producer(self, producer_id: str) -> List[Bottle]:
        return [b for b in self.bottles if producer_id in b.producer_ids]

    def cellared(self) -> List[Bottle]:
        return [b for b in self.bottles if b.status == CellarStatus.CELLARED]

    def undrunk(self) -> List[Bottle]:
        return [b for b in self.bottles if b.status != CellarStatus.DRUNK]

    def ready_now(self, year: int | None = None) -> List[Bottle]:
        return [
            b for b in self.bottles
            if b.status == CellarStatus.CELLARED and b.is_ready(year)
        ]

    def recently_finished(self, n: int = 10) -> List[Bottle]:
        done = [b for b in self.bottles if b.finished_at]
        done.sort(key=lambda b: b.finished_at or "", reverse=True)
        return done[:n]

    def sort_by_title(self) -> List[Bottle]:
        return sorted(self.bottles, key=lambda b: b.title.lower())

    def by_varietal(self, varietal: str) -> List[Bottle]:
        v = varietal.lower()
        return [b for b in self.bottles if b.varietal.lower() == v]

    def filter_vintage_range(self, lo: int, hi: int) -> List[Bottle]:
        return [b for b in self.bottles if b.vintage is not None and lo <= b.vintage <= hi]

    def with_lwin(self) -> List[Bottle]:
        return [b for b in self.bottles if b.lwin]

    def group_by_status(self) -> dict[CellarStatus, List[Bottle]]:
        out: dict[CellarStatus, List[Bottle]] = {}
        for b in self.bottles:
            out.setdefault(b.status, []).append(b)
        return out

    def summary(self) -> str:
        lines = ["Cellar (%d bottles)" % len(self.bottles)]
        groups = self.group_by_status()
        for st in CellarStatus:
            if st in groups:
                lines.append("  %s: %d" % (st.value, len(groups[st])))
        return "\n".join(lines)
