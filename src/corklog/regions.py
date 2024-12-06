"""Region metadata and lookup helpers."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import TYPE_CHECKING, Any, List, Optional
import uuid

from corklog.validators import require_non_empty, validate_url
from corklog.errors import NotFoundError, ConflictError

if TYPE_CHECKING:
    from corklog.storage import JsonStorage


@dataclass
class Region:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    country: str = ""
    website: str = ""
    imprint: str = ""

    def __post_init__(self) -> None:
        self.name = require_non_empty(self.name, "name")
        if self.website:
            self.website = validate_url(self.website)

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "Region":
        pid = kwargs.pop("id", None) or uuid.uuid4().hex[:10]
        return cls(id=pid, name=name.strip(), **kwargs)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Region:
        return cls(**{k: data.get(k) for k in cls.__dataclass_fields__ if k in data or k == "name"})

    def matches(self, q: str) -> bool:
        ql = q.lower()
        return ql in self.name.lower() or ql in self.imprint.lower()

    def display(self) -> str:
        if self.imprint and self.imprint != self.name:
            return "%s (%s)" % (self.imprint, self.name)
        return self.name


class RegionsManager:
    def __init__(self, storage: "JsonStorage"):
        self.storage = storage

    def list_all(self) -> List[Region]:
        return self.storage.list_regions()

    def get(self, pub_id: str) -> Region:
        for p in self.list_all():
            if p.id == pub_id:
                return p
        raise NotFoundError("region", pub_id)

    def find_by_name(self, name: str) -> Optional[Region]:
        nm = name.lower()
        for p in self.list_all():
            if p.name.lower() == nm:
                return p
        return None

    def create(self, name: str, **kwargs: Any) -> Region:
        existing = self.find_by_name(name)
        if existing:
            raise ConflictError("region exists: %s" % name)
        pub = Region.create(name, **kwargs)
        self.storage.upsert_region(pub)
        return pub

    def find_or_create(self, name: str) -> Region:
        p = self.find_by_name(name)
        if p:
            return p
        return self.create(name)

    def bottles_for(self, pub_id: str) -> List[str]:
        return [b.id for b in self.storage.list_bottles() if b.region_id == pub_id]

    def attach_to_bottle(self, bottle_id: str, region_name: str) -> None:
        pub = self.find_or_create(region_name)
        bottle = self.storage.get_bottle(bottle_id)
        bottle.region_id = pub.id
        self.storage.upsert_bottle(bottle)

    def search(self, query: str) -> List[Region]:
        return [p for p in self.list_all() if p.matches(query)]

    def summary(self) -> str:
        lines = ["Regions (%d)" % len(self.list_all())]
        for p in sorted(self.list_all(), key=lambda x: x.name.lower())[:30]:
            n = len(self.bottles_for(p.id))
            lines.append("  %s — %d bottle(s)" % (p.display(), n))
        return "\n".join(lines)


class RegionIndex(RegionsManager):
    """Index view used by importers and tests."""

    def list_all(self) -> List[Region]:
        return sorted(self.storage.list_regions(), key=lambda p: p.name.lower())

    def assign_bottle(self, bottle_id: str, region_name: str) -> None:
        self.attach_to_bottle(bottle_id, region_name)

    def export_csv_lines(self) -> List[str]:
        lines = ["name,id,bottles"]
        for p in sorted(self.list_all(), key=lambda x: x.name.lower()):
            lines.append("%s,%s,%d" % (p.name, p.id, len(self.bottles_for(p.id))))
        return lines
