"""Wishlists — curated lists with optional visibility."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, List, Optional
import uuid

from corklog.validators import require_non_empty, validate_slug
from corklog.errors import NotFoundError, ConflictError


@dataclass
class Wishlist:
    name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    description: str = ""
    bottle_ids: list[str] = field(default_factory=list)
    is_default: bool = False
    is_public: bool = False
    sort_order: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        self.name = require_non_empty(self.name, "name")

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "Wishlist":
        sid = kwargs.pop("id", None) or uuid.uuid4().hex[:10]
        return cls(id=sid, name=name.strip(), **kwargs)

    @property
    def slug(self) -> str:
        return validate_slug(self.name)

    def add_bottle(self, bottle_id: str) -> bool:
        if bottle_id in self.bottle_ids:
            return False
        self.bottle_ids.append(bottle_id)
        return True

    def remove_bottle(self, bottle_id: str) -> bool:
        try:
            self.bottle_ids.remove(bottle_id)
            return True
        except ValueError:
            return False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Wishlist:
        created = data.get("created_at")
        if created:
            data = dict(data)
            data["created_at"] = datetime.fromisoformat(created)
        return cls(**{k: data[k] for k in data if k in cls.__dataclass_fields__})

    def count(self) -> int:
        return len(self.bottle_ids)


class WishlistManager:
    def __init__(self, storage: "JsonStorage"):
        self.storage = storage

    def list_all(self) -> List[Wishlist]:
        return sorted(self.storage.list_wishlists(), key=lambda s: s.sort_order)

    def get(self, wishlist_id: str) -> Wishlist:
        for s in self.list_all():
            if s.id == wishlist_id or s.id.startswith(wishlist_id):
                return s
        raise NotFoundError("wishlist", wishlist_id)

    def find_by_name(self, name: str) -> Optional[Wishlist]:
        nm = name.lower()
        for s in self.list_all():
            if s.name.lower() == nm:
                return s
        return None

    def create(self, name: str, description: str = "") -> Wishlist:
        if self.find_by_name(name):
            raise ConflictError("wishlist exists: %s" % name)
        sh = Wishlist.create(name, description=description, sort_order=len(self.list_all()))
        self.storage.upsert_wishlist(sh)
        return sh

    def add_bottle(self, wishlist_id: str, bottle_id: str) -> None:
        sh = self.get(wishlist_id)
        bottle = self.storage.get_bottle(bottle_id)
        sh.add_bottle(bottle.id)
        if sh.id not in bottle.wishlist_ids:
            bottle.wishlist_ids.append(sh.id)
        self.storage.upsert_wishlist(sh)
        self.storage.upsert_bottle(bottle)

    def remove_bottle(self, wishlist_id: str, bottle_id: str) -> None:
        sh = self.get(wishlist_id)
        sh.remove_bottle(bottle_id)
        bottle = self.storage.get_bottle(bottle_id)
        if wishlist_id in bottle.wishlist_ids:
            bottle.wishlist_ids.remove(wishlist_id)
        self.storage.upsert_wishlist(sh)
        self.storage.upsert_bottle(bottle)

    def default_wishlist(self) -> Wishlist:
        for s in self.list_all():
            if s.is_default:
                return s
        sh = Wishlist.create("To Buy", is_default=True, sort_order=0)
        self.storage.upsert_wishlist(sh)
        return sh

    def report(self, wishlist_id: str) -> str:
        sh = self.get(wishlist_id)
        lines = ["Wishlist: %s" % sh.name, sh.description or "", ""]
        for bid in sh.bottle_ids:
            try:
                b = self.storage.get_bottle(bid)
                lines.append("  - %s [%s]" % (b.title, b.status.value))
            except NotFoundError:
                lines.append("  - (missing %s)" % bid[:8])
        lines.append("")
        lines.append("Total: %d" % sh.count())
        return "\n".join(lines)
