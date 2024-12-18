"""Named collections — curated groups beyond wishlists."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional
import uuid

from corklog.validators import require_non_empty
from corklog.errors import NotFoundError, ConflictError

if TYPE_CHECKING:
    from corklog.storage import JsonStorage

if TYPE_CHECKING:
    from corklog.storage import JsonStorage


@dataclass
class Collection:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    description: str = ""
    bottle_ids: list[str] = field(default_factory=list)
    smart_query: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        self.name = require_non_empty(self.name, "name")

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "Collection":
        cid = kwargs.pop("id", None) or uuid.uuid4().hex[:10]
        return cls(id=cid, name=name.strip(), **kwargs)

    def includes(self, bottle_id: str) -> bool:
        return bottle_id in self.bottle_ids

    def add(self, bottle_id: str) -> None:
        if bottle_id not in self.bottle_ids:
            self.bottle_ids.append(bottle_id)

    def remove(self, bottle_id: str) -> None:
        if bottle_id in self.bottle_ids:
            self.bottle_ids.remove(bottle_id)

    def size(self) -> int:
        return len(self.bottle_ids)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Collection:
        kw = dict(data)
        if kw.get("created_at"):
            kw["created_at"] = datetime.fromisoformat(kw["created_at"])
        return cls(**{k: kw[k] for k in kw if k in cls.__dataclass_fields__})


class CollectionsManager:
    """CRUD wrapper — keeps storage calls in one place."""

    def __init__(self, storage: "JsonStorage"):
        self.storage = storage

    def list_all(self) -> List[Collection]:
        return self.storage.list_collections()

    def get(self, coll_id: str) -> Collection:
        for c in self.list_all():
            if c.id == coll_id:
                return c
        raise NotFoundError("collection", coll_id)

    def create(self, name: str, description: str = "") -> Collection:
        for c in self.list_all():
            if c.name.lower() == name.lower():
                raise ConflictError("collection exists: %s" % name)
        coll = Collection.create(name, description=description)
        self.storage.upsert_collection(coll)
        return coll

    def add_bottle(self, coll_id: str, bottle_id: str) -> None:
        coll = self.get(coll_id)
        self.storage.get_bottle(bottle_id)  # validate
        coll.add(bottle_id)
        self.storage.upsert_collection(coll)

    def remove_bottle(self, coll_id: str, bottle_id: str) -> None:
        coll = self.get(coll_id)
        coll.remove(bottle_id)
        self.storage.upsert_collection(coll)

    def bottles_in(self, coll_id: str) -> List[str]:
        return list(self.get(coll_id).bottle_ids)

    def find_by_name(self, name: str) -> Optional[Collection]:
        nm = name.lower()
        for c in self.list_all():
            if c.name.lower() == nm:
                return c
        return None

    # TODO: evaluate smart_query against SearchEngine
