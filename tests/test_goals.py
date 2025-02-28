"""Tests for corklog.goals."""

from datetime import date

import pytest
from corklog.bottle import Bottle, CellarStatus
from corklog.goals import CellarGoal, GoalsManager
from corklog.tasting import Tasting


def test_reading_goal_create():
    g = CellarGoal.create("Read more", "bottles", 12, "year")
    assert g.target == 12
    assert g.goal_type == "bottles"


def test_pct_complete_zero_target():
    g = CellarGoal.create("X", "bottles", 0, "week")
    assert g.pct_complete() == 100.0


def test_pct_complete_half():
    g = CellarGoal.create("X", "bottles", 10, "year")
    g.progress = 5
    assert g.pct_complete() == 50.0


def test_pct_complete_capped():
    g = CellarGoal.create("X", "bottles", 10, "year")
    g.progress = 99
    assert g.pct_complete() == 100.0


def test_in_range():
    g = CellarGoal.create("X", "bottles", 5, "year")
    assert g.in_range(date(2025, 6, 1)) is True


def test_to_dict_roundtrip():
    g = CellarGoal.create("Y", "minutes", 1000, "month")
    g2 = CellarGoal.from_dict(g.to_dict())
    assert g2.name == g.name


def test_goals_manager_add(json_storage):
    mgr = GoalsManager(json_storage)
    g = CellarGoal.create("Z", "bottles", 3, "week")
    mgr.add_goal(g)
    assert len(mgr.list_goals()) == 1


def test_goals_manager_save(json_storage):
    mgr = GoalsManager(json_storage)
    g = CellarGoal.create("A", "minutes", 600, "week")
    mgr.add_goal(g)
    mgr.save_goals(mgr.list_goals())
    assert len(mgr.list_goals()) == 1


def test_compute_progress_bottles(json_storage, sample_finished_bottle):
    json_storage.upsert_bottle(sample_finished_bottle)
    g = CellarGoal.create(
        "bottles",
        "bottles",
        5,
        "year",
        start_date="2025-01-01",
        end_date="2025-12-31",
    )
    mgr = GoalsManager(json_storage)
    prog = mgr.compute_progress(g)
    assert prog >= 1


def test_compute_progress_volume_ml(json_storage, sample_reading_bottle):
    json_storage.upsert_bottle(sample_reading_bottle)
    sess = Tasting.create(
        sample_reading_bottle.id,
        ml_start=0,
        ml_end=40,
        started_at="2025-05-10T20:00:00",
    )
    json_storage.add_tasting(sess)
    g = CellarGoal.create(
        "volume_ml",
        "volume_ml",
        100,
        "month",
        start_date="2025-05-01",
        end_date="2025-05-31",
    )
    mgr = GoalsManager(json_storage)
    assert mgr.compute_progress(g) == 40


def test_compute_progress_tastings(json_storage, sample_reading_bottle):
    json_storage.upsert_bottle(sample_reading_bottle)
    sess = Tasting.create(
        sample_reading_bottle.id,
        ml_start=0,
        ml_end=10,
        started_at="2025-05-08T20:00:00",
    )
    json_storage.add_tasting(sess)
    g = CellarGoal.create(
        "tastings",
        "tastings",
        10,
        "week",
        start_date="2025-05-05",
        end_date="2025-05-11",
    )
    mgr = GoalsManager(json_storage)
    assert mgr.compute_progress(g) == 1


def test_refresh_all_marks_complete(json_storage, sample_finished_bottle):
    json_storage.upsert_bottle(sample_finished_bottle)
    g = CellarGoal.create(
        "one",
        "bottles",
        1,
        "year",
        start_date="2025-01-01",
        end_date="2025-12-31",
    )
    mgr = GoalsManager(json_storage)
    mgr.add_goal(g)
    updated = mgr.refresh_all()
    assert updated[0].progress >= 1
    assert updated[0].completed is True


def test_period_year_dates():
    g = CellarGoal.create("annual", "bottles", 10, "year")
    assert g.start_date.endswith("-01-01")


def test_period_month_dates():
    g = CellarGoal.create("monthly", "minutes", 500, "month")
    assert len(g.start_date) == 10


def test_period_week_dates():
    g = CellarGoal.create("weekly", "minutes", 120, "week")
    assert g.start_date <= g.end_date


def test_recurring_id_optional():
    g = CellarGoal.create("r", "bottles", 1, "year", recurring_id="rec-1")
    assert g.recurring_id == "rec-1"


def test_progress_default_zero():
    g = CellarGoal.create("new", "bottles", 5, "year")
    assert g.progress == 0


def test_completed_default_false():
    g = CellarGoal.create("new", "bottles", 5, "year")
    assert g.completed is False


def test_list_goals_empty(json_storage):
    mgr = GoalsManager(json_storage)
    assert mgr.list_goals() == []

import pytest
from corklog.errors import NotFoundError


def test_goals_get(empty_storage):
    gm = GoalsManager(empty_storage)
    g = CellarGoal.create("G", "bottles", 3, "year")
    gm.add_goal(g)
    assert gm.get(g.id).name == "G"


def test_goals_get_missing(empty_storage):
    with pytest.raises(NotFoundError):
        GoalsManager(empty_storage).get("missing")


def test_goals_delete(empty_storage):
    gm = GoalsManager(empty_storage)
    g = CellarGoal.create("G", "bottles", 3, "year")
    gm.add_goal(g)
    gm.delete(g.id)
    assert gm.list_goals() == []


def test_goals_delete_missing(empty_storage):
    with pytest.raises(NotFoundError):
        GoalsManager(empty_storage).delete("nope")


def test_compute_progress_tastings_month(empty_storage, sample_bottle):
    empty_storage.upsert_bottle(sample_bottle)
    sess = Tasting.create(
        sample_bottle.id,
        ml_start=0,
        ml_end=10,
        started_at="2026-05-01T10:00:00",
    )
    empty_storage.add_tasting(sess)
    g = CellarGoal.create("Tastings", "tastings", 10, "month", start_date="2026-05-01", end_date="2026-05-31")
    assert GoalsManager(empty_storage).compute_progress(g) == 1


def test_active_goals(empty_storage, sample_read_bottle):
    empty_storage.upsert_bottle(sample_read_bottle)
    g = CellarGoal.create("A", "bottles", 1, "year", start_date="2025-01-01", end_date="2025-12-31")
    gm = GoalsManager(empty_storage)
    gm.add_goal(g)
    gm.refresh_all()
    assert gm.active_goals() == []


def test_days_left_and_pace():
    g = CellarGoal.create("P", "bottles", 10, "year", end_date="2099-12-31")
    assert g.days_left() > 0
    assert g.pace_needed() >= 0


def test_summary_line(empty_storage):
    g = CellarGoal.create("S", "bottles", 10, "year")
    g.progress = 2
    line = GoalsManager(empty_storage).summary_line(g)
    assert "2/10" in line
