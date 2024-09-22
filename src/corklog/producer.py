"""Producer model and helpers."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
import uuid

from corklog.validators import require_non_empty, validate_email
from corklog.errors import NotFoundError, ConflictError


@dataclass
class Producer:
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    bio: str = ""
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    website: str = ""
    email: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    bottle_ids: List[str] = field(default_factory=list)

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> "Producer":
        nm = require_non_empty(name, "name")
        aid = kwargs.pop("id", None) or str(uuid.uuid4())
        email = validate_email(kwargs.get("email"))
        return cls(id=aid, name=nm, email=email, **{k: v for k, v in kwargs.items() if k != "email"})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Producer":
        return cls(
            id=data["id"],
            name=data["name"],
            bio=data.get("bio", ""),
            birth_year=data.get("birth_year"),
            death_year=data.get("death_year"),
            website=data.get("website", ""),
            email=data.get("email"),
            aliases=list(data.get("aliases", [])),
            bottle_ids=list(data.get("bottle_ids", [])),
        )

    def display_name(self) -> str:
        if self.birth_year:
            return "%s (%d–%s)" % (self.name, self.birth_year, self.death_year or "")
        return self.name

    def add_bottle(self, bottle_id: str) -> None:
        if bottle_id not in self.bottle_ids:
            self.bottle_ids.append(bottle_id)

    def remove_bottle(self, bottle_id: str) -> None:
        if bottle_id in self.bottle_ids:
            self.bottle_ids.remove(bottle_id)

    def merge_aliases(self, other: List[str]) -> None:
        for a in other:
            al = a.strip()
            if al and al not in self.aliases:
                self.aliases.append(al)

    def matches(self, query: str) -> bool:
        q = query.lower()
        if q in self.name.lower():
            return True
        return any(q in a.lower() for a in self.aliases)


class ProducerManager:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def list_all(self) -> List[Producer]:
        return sorted(self.storage.list_producers(), key=lambda a: a.name.lower())

    def get(self, producer_id: str) -> Producer:
        for a in self.list_all():
            if a.id == producer_id:
                return a
        raise NotFoundError("producer", producer_id)

    def find_by_name(self, name: str) -> Optional[Producer]:
        nm = name.lower()
        for a in self.list_all():
            if a.name.lower() == nm:
                return a
            if any(nm == al.lower() for al in a.aliases):
                return a
        return None

    def create(self, name: str, **kwargs: Any) -> Producer:
        if self.find_by_name(name):
            raise ConflictError("producer exists: %s" % name)
        au = Producer.create(name, **kwargs)
        self.storage.upsert_producer(au)
        return au

    def find_or_create(self, name: str) -> Producer:
        au = self.find_by_name(name)
        if au:
            return au
        return self.create(name)

    def attach_bottle(self, producer_id: str, bottle_id: str) -> None:
        au = self.get(producer_id)
        bottle = self.storage.get_bottle(bottle_id)
        au.add_bottle(bottle.id)
        if producer_id not in bottle.producer_ids:
            bottle.producer_ids.append(producer_id)
        self.storage.upsert_producer(au)
        self.storage.upsert_bottle(bottle)

    def bottles_for(self, producer_id: str) -> List[str]:
        return [b.id for b in self.storage.list_bottles() if producer_id in b.producer_ids]

    def report(self) -> str:
        lines = ["=== Producers ==="]
        for au in self.list_all():
            n = len(self.bottles_for(au.id))
            lines.append("  %s — %d bottle(s)" % (au.display_name(), n))
        return "\n".join(lines)


def sort_producers(producers: List[Producer]) -> List[Producer]:
    return sorted(producers, key=lambda a: a.name.lower())
