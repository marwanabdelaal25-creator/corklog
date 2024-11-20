"""Bottle vertical tracking."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import TYPE_CHECKING, Any, List, Optional, Set
import uuid

from corklog.validators import require_non_empty
from corklog.errors import NotFoundError, ConflictError
from corklog.bottle import CellarStatus

if TYPE_CHECKING:
    from corklog.storage import JsonStorage


@dataclass
class Vertical:
    title: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    producer_id: str | None = None
    total_planned: int | None = None
    description: str = ""
    bottle_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.title = require_non_empty(self.title, "title")

    @classmethod
    def create(cls, title: str, **kwargs: Any) -> "Vertical":
        sid = kwargs.pop("id", None) or uuid.uuid4().hex[:10]
        return cls(id=sid, title=title.strip(), **kwargs)

    def add_volume(self, bottle_id: str) -> None:
        if bottle_id not in self.bottle_ids:
            self.bottle_ids.append(bottle_id)

    def remove_volume(self, bottle_id: str) -> None:
        if bottle_id in self.bottle_ids:
            self.bottle_ids.remove(bottle_id)

    def completion_pct(self, drunk_ids: Set[str]) -> float:
        if not self.bottle_ids:
            return 0.0
        got = sum(1 for bid in self.bottle_ids if bid in drunk_ids)
        return round(100.0 * got / len(self.bottle_ids), 1)

    def next_undrunk(self, drunk_ids: Set[str] | "JsonStorage") -> Optional[str]:
        if hasattr(drunk_ids, "list_bottles"):
            drunk_ids = {
                b.id for b in drunk_ids.list_bottles() if b.status == CellarStatus.DRUNK
            }
        for bid in self.bottle_ids:
            if bid not in drunk_ids:
                return bid
        return None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Vertical:
        return cls(**{k: data[k] for k in data if k in cls.__dataclass_fields__})


class VerticalManager:
    def __init__(self, storage: "JsonStorage"):
        self.storage = storage

    def list_all(self) -> List[Vertical]:
        return self.storage.list_vertical()

    def get(self, vertical_id: str) -> Vertical:
        for s in self.list_all():
            if s.id == vertical_id:
                return s
        raise NotFoundError("vertical", vertical_id)

    def create(self, title: str, producer_id: Optional[str] = None) -> Vertical:
        for s in self.list_all():
            if s.title.lower() == title.lower():
                raise ConflictError("vertical exists: %s" % title)
        ser = Vertical.create(title, producer_id=producer_id)
        self.storage.upsert_vertical(ser)
        return ser

    def add_bottle(self, vertical_id: str, bottle_id: str, index: Optional[float] = None) -> None:
        ser = self.get(vertical_id)
        ser.add_volume(bottle_id)
        try:
            bottle = self.storage.get_bottle(bottle_id)
            bottle.vertical_id = vertical_id
            if index is not None:
                bottle.vertical_index = index
            self.storage.upsert_bottle(bottle)
        except NotFoundError:
            pass
        self.storage.upsert_vertical(ser)

    def drunk_ids(self) -> Set[str]:
        return {b.id for b in self.storage.list_bottles() if b.status == CellarStatus.DRUNK}

    def progress_report(self) -> str:
        lines = ["=== Vertical progress ==="]
        read = self.drunk_ids()
        for ser in sorted(self.list_all(), key=lambda s: s.title.lower()):
            pct = ser.completion_pct(read)
            nxt = ser.next_undrunk(self.storage)
            nxt_title = ""
            if nxt:
                try:
                    nxt_title = self.storage.get_bottle(nxt).title
                except NotFoundError:
                    nxt_title = nxt[:8]
            lines.append(
                "{title}: {pct:.0f}% ({n}/{tot}) next={nxt}".format(
                    title=ser.title,
                    pct=pct,
                    n=sum(1 for b in ser.bottle_ids if b in read),
                    tot=len(ser.bottle_ids),
                    nxt=nxt_title or "-",
                )
            )
        return "\n".join(lines)


class VerticalRegistry(VerticalManager):
    """Test-friendly alias for vertical operations."""

    def attach_bottle(self, vertical_id: str, bottle_id: str, index: Optional[float] = None) -> None:
        self.add_bottle(vertical_id, bottle_id, index=index)

    def find_by_title(self, query: str) -> Optional[Vertical]:
        ql = query.lower()
        for s in self.list_all():
            if ql in s.title.lower():
                return s
        return None

    def progress_report_lines(self) -> List[str]:
        return self.progress_report().splitlines()
