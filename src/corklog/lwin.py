"""LWIN (Liv-ex Wine Identification Number) parsing and validation.

LWIN is the wine trade's standard identifier. It comes in a few lengths:

  * 7 digits  — the wine (producer + label), e.g. ``1011266``
  * 11 digits — wine + vintage (7 + 4-digit year)
  * 16 digits — wine + vintage + pack size + bottle size
  * 18 digits — the full "LWIN18"

We accept any of those, ignoring spaces/dashes, and expose the parts.
"""

from __future__ import annotations

import re

VALID_LENGTHS = (7, 11, 16, 18)
_SEP = re.compile(r"[\s\-]")


def _digits(raw: str) -> str:
    return _SEP.sub("", (raw or "").strip())


def is_lwin(value: str) -> bool:
    d = _digits(str(value))
    return d.isdigit() and len(d) in VALID_LENGTHS


def validate_lwin(value: str) -> bool:
    if not value or not str(value).strip():
        return False
    return is_lwin(value)


def normalize_lwin(value: str) -> str:
    d = _digits(str(value))
    if not (d.isdigit() and len(d) in VALID_LENGTHS):
        raise ValueError("not a valid LWIN: %r" % value)
    return d


def normalize(raw: str) -> str | None:
    if not raw or not str(raw).strip():
        return None
    try:
        return normalize_lwin(raw)
    except ValueError:
        return None


def parse(raw: str) -> str | None:
    return normalize(raw)


def base7(value: str) -> str | None:
    """The 7-digit wine root, dropping vintage/pack/size if present."""
    n = normalize(value)
    if n is None:
        return None
    return n[:7]


def vintage_part(value: str) -> int | None:
    n = normalize(value)
    if n is None or len(n) < 11:
        return None
    yr = int(n[7:11])
    return yr or None


def lwin_kind(value: str) -> str:
    n = normalize(value)
    if n is None:
        return "unknown"
    return {7: "lwin7", 11: "lwin11", 16: "lwin16", 18: "lwin18"}[len(n)]


def format_display(value: str) -> str:
    n = normalize(value)
    if n is None:
        return value
    if len(n) >= 11:
        yr = vintage_part(n)
        return "LWIN %s (%s)" % (n[:7], yr if yr else "NV")
    return "LWIN %s" % n


def guess_lwin(text: str) -> str | None:
    for token in re.findall(r"\d[\d\s\-]{5,}\d", text or ""):
        if validate_lwin(token):
            return normalize_lwin(token)
    return None


def clean_id_list(raw: str) -> list[str]:
    out: list[str] = []
    for part in (raw or "").replace(";", ",").split(","):
        p = part.strip()
        if not p:
            continue
        try:
            out.append(normalize_lwin(p))
        except ValueError:
            continue
    return out


def batch_validate(values: list[str]) -> dict[str, bool]:
    return {v: validate_lwin(v) for v in values}


def compare_lwin(a: str, b: str) -> bool:
    na, nb = base7(a), base7(b)
    if na is None or nb is None:
        return False
    return na == nb


def explain(value: str) -> str:
    if not value or not str(value).strip():
        return "empty id"
    if not validate_lwin(value):
        return "invalid lwin"
    return "valid %s -> %s" % (lwin_kind(value), normalize_lwin(value))


# aliases some callers reach for
validate = validate_lwin
is_valid = validate_lwin
format_lwin = format_display
clean = _digits
