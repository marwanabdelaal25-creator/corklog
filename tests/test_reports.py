"""Tests for corklog.reports."""

import pytest
from corklog.reports import ReportBuilder, _bar
from corklog.goals import CellarGoal, GoalsManager


def test_bar_empty():
    assert _bar(0.0) == "[--------------------]"


def test_bar_full():
    assert _bar(100.0) == "[####################]"


def test_bar_half():
    b = _bar(50.0, width=10)
    assert b.count("#") == 5


def test_overview_contains_title(populated_json_storage):
    rb = ReportBuilder(populated_json_storage)
    text = rb.overview()
    assert "Corklog" in text


def test_status_report_all(populated_json_storage):
    rb = ReportBuilder(populated_json_storage)
    text = rb.status_report()
    assert "Margaux" in text or "Grange" in text


def test_status_report_filtered(populated_json_storage):
    rb = ReportBuilder(populated_json_storage)
    text = rb.status_report(status="want")
    assert "Margaux" in text or "No bottles" in text


def test_status_report_empty(json_storage):
    rb = ReportBuilder(json_storage)
    assert rb.status_report() == "No bottles match."


def test_goals_report_empty(json_storage):
    rb = ReportBuilder(json_storage)
    assert "No goals" in rb.goals_report()


def test_goals_report_with_goal(json_storage):
    mgr = GoalsManager(json_storage)
    mgr.add_goal(CellarGoal.create("Read 5", "bottles", 5, "year"))
    rb = ReportBuilder(json_storage)
    text = rb.goals_report()
    assert "Read 5" in text


def test_yearly_summary(populated_json_storage):
    rb = ReportBuilder(populated_json_storage)
    text = rb.yearly_summary(2025)
    assert "2025" in text
    assert "Drunk" in text


def test_yearly_summary_default_year(populated_json_storage):
    rb = ReportBuilder(populated_json_storage)
    text = rb.yearly_summary()
    assert "summary" in text.lower()


def test_export_text_combines(populated_json_storage):
    rb = ReportBuilder(populated_json_storage)
    text = rb.export_text()
    assert "Overview" in text or "Corklog" in text


def test_overview_includes_status_breakdown(populated_json_storage):
    rb = ReportBuilder(populated_json_storage)
    text = rb.overview()
    assert "By status" in text


def test_goals_report_shows_bar(json_storage):
    GoalsManager(json_storage).add_goal(CellarGoal.create("G", "minutes", 100, "month"))
    text = ReportBuilder(json_storage).goals_report()
    assert "[" in text and "]" in text


def test_status_report_progress_column(populated_json_storage):
    text = ReportBuilder(populated_json_storage).status_report(status="open")
    assert "%" in text or "-" in text


def test_yearly_summary_volume_ml(populated_json_storage):
    text = ReportBuilder(populated_json_storage).yearly_summary(2025)
    assert "Volume" in text


def test_bar_custom_width():
    assert len(_bar(25.0, width=4)) == 6  # [##--]


def test_report_builder_goals_manager(json_storage):
    rb = ReportBuilder(json_storage)
    assert rb.goals is not None


def test_status_report_sorted(populated_json_storage):
    text = ReportBuilder(populated_json_storage).status_report()
    lines = text.splitlines()
    assert lines[0].startswith("Wine")


def test_goals_report_percent(populated_json_storage):
    text = ReportBuilder(populated_json_storage).goals_report()
    assert "%" in text


def test_overview_multiline(populated_json_storage):
    text = ReportBuilder(populated_json_storage).overview()
    assert text.count("\n") >= 3

from corklog.reports import ReportBuilder


from corklog.notes import Note
from corklog.quotes import Quote


def test_overview(populated_storage):
    text = ReportBuilder(populated_storage).overview()
    assert "Overview" in text


def test_status_report_filtered(populated_storage):
    text = ReportBuilder(populated_storage).status_report(status="drunk")
    assert isinstance(text, str)


def test_goals_report_empty(empty_storage):
    assert "No goals" in ReportBuilder(empty_storage).goals_report()


def test_recent_tastings(populated_storage, sample_tasting):
    populated_storage.add_tasting(sample_tasting)
    text = ReportBuilder(populated_storage).recent_tastings(limit=5)
    assert "tastings" in text.lower()


def test_quotes_digest(populated_storage, sample_bottle):
    populated_storage.add_quote(Quote(text="Line", bottle_id=sample_bottle.id))
    assert ReportBuilder(populated_storage).quotes_digest()


def test_notes_digest_bottle(populated_storage, sample_bottle):
    populated_storage.add_note(Note.create("body", sample_bottle.id, title="N"))
    md = ReportBuilder(populated_storage).notes_digest(sample_bottle.id)
    assert sample_bottle.title in md or "body" in md


def test_notes_digest_all(populated_storage, sample_bottle):
    populated_storage.add_note(Note.create("all notes", sample_bottle.id))
    text = ReportBuilder(populated_storage).notes_digest()
    assert "Notes" in text


def test_region_report(populated_storage):
    assert isinstance(ReportBuilder(populated_storage).region_report(), str)


def test_export_markdown(populated_storage):
    md = ReportBuilder(populated_storage).export_markdown()
    assert "# My Cellar" in md


def test_compare_years_report(populated_storage):
    assert "vs" in ReportBuilder(populated_storage).compare_years(2024, 2025)


def test_full_digest(populated_storage):
    text = ReportBuilder(populated_storage).full_digest()
    assert "Overview" in text


def test_drink_tonight_ready(empty_storage):
    from corklog.bottle import Bottle, CellarStatus

    empty_storage.upsert_bottle(Bottle.create("Ready Now", drink_from=2020, drink_to=2030, status=CellarStatus.CELLARED))
    empty_storage.upsert_bottle(Bottle.create("Too Young", drink_from=2035, drink_to=2050, status=CellarStatus.CELLARED))
    out = ReportBuilder(empty_storage).drink_tonight(year=2026)
    assert "Ready Now" in out
    assert "Too Young" not in out


def test_drink_tonight_none(empty_storage):
    out = ReportBuilder(empty_storage).drink_tonight()
    assert "Nothing in the cellar" in out


def test_export_markdown_shows_rating_value(populated_json_storage):
    md = ReportBuilder(populated_json_storage).export_markdown()
    # the rating must render as a number, never the Rating object repr
    assert "Rating(" not in md
