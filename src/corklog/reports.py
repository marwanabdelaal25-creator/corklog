"""Text reports for terminal output."""

from __future__ import annotations

from datetime import date
from typing import Optional

from corklog.bottle import CellarStatus
from corklog.goals import GoalsManager
from corklog.stats import compute_stats, ready_to_drink
from corklog.streaks import compute_streak
from corklog.storage import JsonStorage
from corklog.quotes import QuotesManager
from corklog.notes import NotesManager
from corklog.vertical import VerticalManager
from corklog.regions import RegionsManager


def _bar(pct: float, width: int = 20) -> str:
    filled = int(width * pct / 100)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


class ReportBuilder:
    def __init__(self, storage: JsonStorage):
        self.storage = storage
        self.goals = GoalsManager(storage)
        self.quotes = QuotesManager(storage)
        self.notes = NotesManager(storage)
        self.vertical = VerticalManager(storage)
        self.regions = RegionsManager(storage)

    def overview(self) -> str:
        st = compute_stats(self.storage)
        streak = compute_streak(self.storage)
        lines = ["=== Corklog Cellar Overview ===", ""]
        lines.extend(st.summary_lines())
        lines.append("")
        lines.append("By status:")
        for k, v in sorted(st.by_status.items()):
            lines.append("  {0}: {1}".format(k, v))
        lines.append("")
        lines.append(streak.as_text())
        return "\n".join(lines)

    def status_report(self, status: Optional[str] = None) -> str:
        bottles = self.storage.list_bottles()
        if status:
            bottles = [b for b in bottles if b.status.value == status]
        bottles.sort(key=lambda b: b.title.lower())
        if not bottles:
            return "No bottles match."
        lines = ["Wine | Status | Drink window", "-" * 48]
        for b in bottles:
            lines.append("{label:<32} | {st:8} | {win}".format(
                label=b.short_label()[:32], st=b.status.value, win=b.drink_window_status(),
            ))
        return "\n".join(lines)

    def goals_report(self) -> str:
        goals = self.goals.refresh_all()
        if not goals:
            return "No goals defined. Set one with `corklog goal-add`."
        lines = ["=== Goals ==="]
        for g in goals:
            pct = g.pct_complete()
            lines.append(
                "{name}: {prog}/{target} {typ} ({pct:.0f}%) {bar}".format(
                    name=g.name, prog=g.progress, target=g.target,
                    typ=g.goal_type, pct=pct, bar=_bar(pct),
                )
            )
        return "\n".join(lines)

    def yearly_summary(self, year: Optional[int] = None) -> str:
        yr = year or date.today().year
        bottles = self.storage.list_bottles()
        finished = [
            b for b in bottles
            if b.status == CellarStatus.DRUNK and b.finished_at and b.finished_at[:4] == str(yr)
        ]
        lines = [
            "Year %d summary" % yr,
            "Drunk: %d bottles" % len(finished),
        ]
        litres = sum(b.volume_ml or 0 for b in finished) / 1000.0
        lines.append("Volume drunk: %.1f L" % litres)
        if finished:
            lines.append("")
            lines.append("Bottles:")
            for b in sorted(finished, key=lambda x: x.finished_at or ""):
                rt = ("%.1f" % b.rating_value) if b.rating_value is not None else "-"
                lines.append("  • %s — %s/5" % (b.short_label(), rt))
        return "\n".join(lines)

    def recent_tastings(self, limit: int = 20) -> str:
        tastings = sorted(
            self.storage.list_tastings(),
            key=lambda s: s.started_at,
            reverse=True,
        )
        by_id = {b.id: b for b in self.storage.list_bottles()}
        lines = ["Recent tastings", "-" * 30]
        for s in tastings[:limit]:
            bk = by_id.get(s.bottle_id)
            title = bk.short_label() if bk else s.bottle_id[:8]
            score = (" — %.1f" % s.score) if s.score is not None else ""
            lines.append(
                "{date} | {title} | {ml}ml{score}".format(
                    date=s.started_at[:10], title=title[:32], ml=s.poured_ml(), score=score,
                )
            )
        return "\n".join(lines)

    def drink_tonight(self, n: int = 5, year: int | None = None) -> str:
        """Cellared bottles that are in their drink window right now —
        soonest-to-fade first, so nothing dies in the rack."""
        ready = ready_to_drink(self.storage, year)
        if not ready:
            return "Nothing in the cellar is ready to drink yet."
        ready.sort(key=lambda b: (b.drink_to if b.drink_to is not None else 9999))
        lines = ["Ready to open tonight:"]
        for b in ready[:n]:
            window = "drink by %d" % b.drink_to if b.drink_to else "ready"
            spot = (" @ %s" % b.cellar_location) if b.cellar_location else ""
            lines.append("  %s — %s%s" % (b.short_label(), window, spot))
        return "\n".join(lines)

    def quotes_digest(self) -> str:
        return self.quotes.export_text()

    def notes_digest(self, bottle_id: Optional[str] = None) -> str:
        if bottle_id:
            return self.notes.export_markdown(bottle_id)
        lines = ["=== Notes across the cellar ==="]
        for n in self.storage.list_notes()[:50]:
            lines.append("- %s: %s" % (n.title or n.id[:8], n.excerpt(60)))
        return "\n".join(lines)

    def vertical_report(self) -> str:
        return self.vertical.progress_report()

    def region_report(self) -> str:
        return self.regions.summary()

    def export_text(self) -> str:
        chunks = [self.overview(), "", self.goals_report(), "", self.vertical_report()]
        return "\n".join(chunks)

    def export_markdown(self) -> str:
        chunks = ["# My Cellar\n", "_Generated by corklog_\n"]
        for b in sorted(self.storage.list_bottles(), key=lambda b: b.title.lower()):
            chunks.append("## %s\n" % b.short_label())
            chunks.append("- Status: %s\n" % b.status.value)
            if b.varietal:
                chunks.append("- Varietal: %s\n" % b.varietal)
            chunks.append("- Drink window: %s\n" % b.drink_window_status())
            if b.rating_value is not None:
                chunks.append("- Score: %s/5\n" % b.rating_value)
            chunks.append("\n")
        return "".join(chunks)

    def compare_years(self, y1: int, y2: int) -> str:
        from corklog.stats import compare_years

        return compare_years(self.storage, y1, y2)

    def full_digest(self) -> str:
        parts = [
            self.overview(), "", self.goals_report(), "", self.vertical_report(),
            "", self.region_report(), "", self.recent_tastings(15),
        ]
        return "\n".join(parts)
