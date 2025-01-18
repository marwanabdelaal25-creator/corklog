"""Aggregate statistics over the cellar."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Any

from corklog.bottle import CellarStatus
from corklog.storage import JsonStorage


@dataclass
class LibraryStats:
    total_bottles: int = 0
    by_status: Dict[str, int] = field(default_factory=dict)
    total_poured_ml: int = 0
    cellar_value: float = 0.0
    avg_rating: Optional[float] = None
    producers_count: int = 0
    tastings_count: int = 0

    def summary_lines(self) -> List[str]:
        lines = [
            "Bottles: %d" % self.total_bottles,
            "Producers: %d" % self.producers_count,
            "Tastings logged: %d" % self.tastings_count,
        ]
        if self.avg_rating is not None:
            lines.append("Average score: %.2f / 5" % self.avg_rating)
        lines.append("Poured all-time: %.1f L" % (self.total_poured_ml / 1000.0))
        lines.append("Cellar value: %.2f" % self.cellar_value)
        return lines


def count_by_status(storage: JsonStorage) -> Dict[str, int]:
    c: Counter[str] = Counter()
    for b in storage.list_bottles():
        c[b.status.value] += 1
    return dict(c)


def poured_ml_in_range(storage: JsonStorage, start: date, end: date) -> int:
    tot = 0
    for s in storage.list_tastings():
        if start <= s.tasting_date <= end:
            tot += s.poured_ml()
    return tot


def avg_bottle_rating(storage: JsonStorage) -> Optional[float]:
    scores = [b.rating_value for b in storage.list_bottles() if b.rating_value is not None]
    if not scores:
        ratings = storage.list_ratings()
        if not ratings:
            return None
        return round(sum(r.value for r in ratings) / len(ratings), 2)
    return round(sum(scores) / len(scores), 2)


def cellar_value(storage: JsonStorage) -> float:
    """Total price of bottles still in the cellar (cellared or open)."""
    total = 0.0
    for b in storage.list_bottles():
        if b.status in (CellarStatus.CELLARED, CellarStatus.OPEN) and b.price:
            total += b.price
    return round(total, 2)


def top_tags(storage: JsonStorage, n: int = 10) -> List[tuple[str, int]]:
    tags = {t.id: t.name for t in storage.list_tags()}
    cnt: Counter[str] = Counter()
    for b in storage.list_bottles():
        for tid in b.tag_ids:
            cnt[tags.get(tid, tid)] += 1
    return cnt.most_common(n)


def pour_pace(storage: JsonStorage, days: int = 30) -> Dict[str, float | int]:
    end = date.today()
    start = end - timedelta(days=days)
    ml = poured_ml_in_range(storage, start, end)
    return {
        "ml": ml,
        "ml_per_day": round(ml / max(days, 1), 1),
        "window_days": days,
    }


def compute_stats(storage: JsonStorage) -> LibraryStats:
    bottles = storage.list_bottles()
    tastings = storage.list_tastings()
    return LibraryStats(
        total_bottles=len(bottles),
        by_status=count_by_status(storage),
        total_poured_ml=sum(s.poured_ml() for s in tastings),
        cellar_value=cellar_value(storage),
        avg_rating=avg_bottle_rating(storage),
        producers_count=len(storage.list_producers()),
        tastings_count=len(tastings),
    )


def format_stats(storage: JsonStorage) -> str:
    st = compute_stats(storage)
    pace = pour_pace(storage)
    parts = ["Cellar stats", "  Total bottles: %d" % st.total_bottles]
    parts.append("  By status: %s" % st.by_status)
    if st.avg_rating is not None:
        parts.append("  Avg score: %.2f" % st.avg_rating)
    parts.append("  Ready to drink: %d" % ready_count(storage))
    parts.append("  Cellar value: %.2f" % st.cellar_value)
    parts.append("  Last 30d poured: %d ml" % pace["ml"])
    return "\n".join(parts)


def bottles_finished_in_year(storage: JsonStorage, year: int) -> int:
    n = 0
    for b in storage.list_bottles():
        if b.status != CellarStatus.DRUNK or not b.finished_at:
            continue
        if b.finished_at[:4] == str(year):
            n += 1
    return n


def _decade(year: int) -> str:
    return "%ds" % (year // 10 * 10)


def decade_distribution(storage: JsonStorage) -> Dict[str, int]:
    """How many bottles per vintage decade (e.g. {'2010s': 12})."""
    c: Counter[str] = Counter()
    for b in storage.list_bottles():
        if b.vintage:
            c[_decade(b.vintage)] += 1
    return dict(c)


def region_distribution(storage: JsonStorage) -> Dict[str, int]:
    names = {r.id: r.name for r in storage.list_regions()}
    c: Counter[str] = Counter()
    for b in storage.list_bottles():
        if b.region_id:
            c[names.get(b.region_id, b.region_id)] += 1
        elif b.country:
            c[b.country] += 1
    return dict(c)


def varietal_distribution(storage: JsonStorage) -> Dict[str, int]:
    c: Counter[str] = Counter()
    for b in storage.list_bottles():
        if b.varietal:
            c[b.varietal] += 1
    return dict(c)


def top_producers(storage: JsonStorage, n: int = 5) -> List[tuple[str, int]]:
    names = {p.id: p.name for p in storage.list_producers()}
    c: Counter[str] = Counter()
    for b in storage.list_bottles():
        for pid in b.producer_ids:
            c[names.get(pid, pid)] += 1
    return c.most_common(n)


def ready_to_drink(storage: JsonStorage, year: int | None = None) -> List[Any]:
    yr = year or date.today().year
    return [
        b for b in storage.list_bottles()
        if b.status == CellarStatus.CELLARED and b.is_ready(yr)
    ]


def ready_count(storage: JsonStorage, year: int | None = None) -> int:
    return len(ready_to_drink(storage, year))


def drink_window_distribution(storage: JsonStorage, year: int | None = None) -> Dict[str, int]:
    yr = year or date.today().year
    c: Counter[str] = Counter()
    for b in storage.list_bottles():
        if b.status in (CellarStatus.CELLARED, CellarStatus.OPEN):
            c[b.drink_window_status(yr)] += 1
    return dict(c)


def average_rating_by_decade(storage: JsonStorage) -> Dict[str, float]:
    buckets: Dict[str, List[float]] = {}
    for b in storage.list_bottles():
        if b.vintage and b.rating_value is not None:
            buckets.setdefault(_decade(b.vintage), []).append(b.rating_value)
    return {dec: round(sum(v) / len(v), 2) for dec, v in buckets.items()}


def value_by_region(storage: JsonStorage) -> Dict[str, float]:
    names = {r.id: r.name for r in storage.list_regions()}
    out: Dict[str, float] = {}
    for b in storage.list_bottles():
        if not b.price:
            continue
        key = names.get(b.region_id, b.region_id) if b.region_id else (b.country or "?")
        out[key] = round(out.get(key, 0.0) + b.price, 2)
    return out


def format_breakdown(storage: JsonStorage) -> str:
    st = compute_stats(storage)
    pace = pour_pace(storage, 30)
    lines = ["=== Detailed stats ===", ""]
    lines.extend(st.summary_lines())
    lines.append("")
    lines.append("Ready to drink now: %d" % ready_count(storage))
    lines.append("30-day poured: %d ml" % pace["ml"])
    decades = decade_distribution(storage)
    if decades:
        lines.append("")
        lines.append("By vintage decade:")
        for dec in sorted(decades):
            lines.append("  %s: %d" % (dec, decades[dec]))
    regions = sorted(region_distribution(storage).items(), key=lambda kv: -kv[1])
    if regions:
        lines.append("")
        lines.append("By region:")
        for name, cnt in regions[:8]:
            lines.append("  %s (%d)" % (name, cnt))
    producers = top_producers(storage, 5)
    if producers:
        lines.append("")
        lines.append("Top producers:")
        for name, cnt in producers:
            lines.append("  %s (%d)" % (name, cnt))
    lines.append("")
    lines.append("Drunk this year: %d" % bottles_finished_in_year(storage, date.today().year))
    return "\n".join(lines)


def monthly_pour(storage: JsonStorage, year: int, month: int) -> int:
    start = date(year, month, 1)
    if month == 12:
        end = date(year, 12, 31)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return poured_ml_in_range(storage, start, end)


def status_percentages(storage: JsonStorage) -> Dict[str, float]:
    counts = count_by_status(storage)
    total = sum(counts.values()) or 1
    return {k: round(100.0 * v / total, 1) for k, v in counts.items()}


def average_price(storage: JsonStorage) -> Optional[float]:
    prices = [b.price for b in storage.list_bottles() if b.price]
    if not prices:
        return None
    return round(sum(prices) / len(prices), 2)


def pour_by_weekday(storage: JsonStorage) -> Dict[int, int]:
    """ml poured per weekday (0=Mon)."""
    ml: Dict[int, int] = {i: 0 for i in range(7)}
    for s in storage.list_tastings():
        ml[s.tasting_date.weekday()] += s.poured_ml()
    return ml


def completion_rate(storage: JsonStorage) -> float:
    bottles = storage.list_bottles()
    if not bottles:
        return 0.0
    drunk = sum(1 for b in bottles if b.status == CellarStatus.DRUNK)
    return round(100.0 * drunk / len(bottles), 1)


def dumped_rate(storage: JsonStorage) -> float:
    bottles = storage.list_bottles()
    if not bottles:
        return 0.0
    dumped = sum(1 for b in bottles if b.status == CellarStatus.DUMPED)
    return round(100.0 * dumped / len(bottles), 1)


def average_pour(storage: JsonStorage) -> Optional[float]:
    pours = [s.poured_ml() for s in storage.list_tastings() if s.poured_ml() > 0]
    if not pours:
        return None
    return round(sum(pours) / len(pours), 1)


def ml_by_month(storage: JsonStorage, year: int) -> Dict[int, int]:
    out: Dict[int, int] = {}
    for m in range(1, 13):
        pg = monthly_pour(storage, year, m)
        if pg:
            out[m] = pg
    return out


def rating_distribution(storage: JsonStorage) -> Dict[int, int]:
    from corklog.rating import histogram

    return histogram(storage.list_ratings())


def format_leaderboard(storage: JsonStorage, n: int = 5) -> str:
    bottles = sorted(
        [b for b in storage.list_bottles() if b.rating_value is not None],
        key=lambda b: b.rating_value or 0,
        reverse=True,
    )[:n]
    if not bottles:
        return "No scored bottles yet."
    lines = ["Top scored:"]
    for b in bottles:
        lines.append("  %.1f — %s" % (b.rating_value, b.short_label()))
    return "\n".join(lines)


def pour_velocity(storage: JsonStorage, weeks: int = 4) -> float:
    pace = pour_pace(storage, weeks * 7)
    return float(pace["ml_per_day"])


class StatsReporter:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def full_report(self) -> str:
        return format_breakdown(self.storage)

    def quick(self) -> str:
        return format_stats(self.storage)

    def entity_counts(self) -> Dict[str, int]:
        return self.storage.count_entities()

    def weekday_chart(self) -> str:
        ml = pour_by_weekday(self.storage)
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        lines = ["ml poured by weekday:"]
        mx = max(ml.values()) or 1
        for i, lbl in enumerate(days):
            bar = "#" * int(20 * ml[i] / mx)
            lines.append("  %s %5dml %s" % (lbl, ml[i], bar))
        return "\n".join(lines)

    def monthly_table(self, year: int) -> str:
        lines = ["ml poured by month (%d)" % year]
        for m in range(1, 13):
            pg = monthly_pour(self.storage, year, m)
            if pg:
                lines.append("  %02d: %5d ml" % (m, pg))
        return "\n".join(lines)

    def decade_chart(self) -> str:
        dist = decade_distribution(self.storage)
        if not dist:
            return "No vintages on file yet."
        avg = average_rating_by_decade(self.storage)
        mx = max(dist.values()) or 1
        lines = ["Bottles by vintage decade:"]
        for dec in sorted(dist):
            bar = "#" * int(20 * dist[dec] / mx)
            score = (" avg %.1f" % avg[dec]) if dec in avg else ""
            lines.append("  %-6s %3d %s%s" % (dec, dist[dec], bar, score))
        return "\n".join(lines)

    def region_chart(self) -> str:
        dist = region_distribution(self.storage)
        if not dist:
            return "No regions on file yet."
        lines = ["Bottles by region:"]
        for name, cnt in sorted(dist.items(), key=lambda kv: -kv[1]):
            lines.append("  %-20s %d" % (name[:20], cnt))
        return "\n".join(lines)

    def export_json_summary(self) -> Dict[str, Any]:
        st = compute_stats(self.storage)
        return {
            "total_bottles": st.total_bottles,
            "by_status": st.by_status,
            "avg_rating": st.avg_rating,
            "cellar_value": st.cellar_value,
            "ready_to_drink": ready_count(self.storage),
            "completion_rate": completion_rate(self.storage),
            "pace_30d": pour_pace(self.storage, 30),
        }


def compare_years(storage: JsonStorage, y1: int, y2: int) -> str:
    b1 = bottles_finished_in_year(storage, y1)
    b2 = bottles_finished_in_year(storage, y2)
    return "Drunk %d (%d) vs %d (%d)" % (y1, b1, y2, b2)
