"""A tasting — one glass/pour from a bottle, with a note and an optional score."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Any, Dict, Optional
import uuid

from corklog.errors import ValidationError


@dataclass
class Tasting:
    bottle_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    ml_start: int = 0
    ml_end: int = 0
    score: Optional[float] = None
    occasion: str = ""
    with_whom: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if self.ml_start < 0 or self.ml_end < 0:
            raise ValidationError("pour amount cannot be negative", field="ml")
        if self.ml_end < self.ml_start:
            raise ValueError("ml_end before ml_start")

    @classmethod
    def create(cls, bottle_id: str, **kwargs: Any) -> "Tasting":
        sid = kwargs.pop("id", None) or str(uuid.uuid4())
        return cls(id=sid, bottle_id=bottle_id, **kwargs)

    def poured_ml(self) -> int:
        return max(0, self.ml_end - self.ml_start)

    @property
    def tasting_date(self) -> date:
        return datetime.fromisoformat(self.started_at[:19]).date()

    def is_blind(self) -> bool:
        return "blind" in (self.occasion or "").lower()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tasting":
        return cls(**{k: data.get(k) for k in cls.__dataclass_fields__ if k in data or k == "bottle_id"})


Session = Tasting  # older imports
