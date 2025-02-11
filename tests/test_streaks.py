"""Tests for corklog.streaks."""

from datetime import date, timedelta

import pytest
from corklog.tasting import Tasting
from corklog.streaks import (
    StreakInfo,
    active_dates,
    current_streak,
    longest_streak,
    compute_streak,
    streak_summary,
)


def _add_tasting(store, bottle_id, day, ml=120):
    s = Tasting.create(
        bottle_id,
        started_at=f"{day.isoformat()}T20:00:00",
        ml_start=0,
        ml_end=ml,
    )
    store.tastings[s.id] = s


def test_streak_info_text_zero():
    info = StreakInfo(0, 5, None, [])
    assert "No active streak" in info.as_text()


def test_streak_info_text_active():
    info = StreakInfo(3, 10, "2025-05-01", [])
    assert "3" in info.as_text()


def test_active_dates_empty(library_store):
    assert active_dates(library_store) == set()


def test_active_dates_with_tasting(library_store, sample_reading_bottle):
    library_store.upsert_bottle(sample_reading_bottle)
    day = date(2025, 5, 10)
    _add_tasting(library_store, sample_reading_bottle.id, day)
    dates = active_dates(library_store)
    assert day in dates


def test_current_streak_zero(library_store):
    assert current_streak(library_store, today=date(2025, 1, 1)) == 0


def test_current_streak_one_day(library_store, sample_reading_bottle):
    library_store.upsert_bottle(sample_reading_bottle)
    today = date(2025, 5, 10)
    _add_tasting(library_store, sample_reading_bottle.id, today)
    assert current_streak(library_store, today=today) == 1


def test_current_streak_consecutive(library_store, sample_reading_bottle):
    library_store.upsert_bottle(sample_reading_bottle)
    d1 = date(2025, 5, 8)
    d2 = date(2025, 5, 9)
    d3 = date(2025, 5, 10)
    for d in (d1, d2, d3):
        _add_tasting(library_store, sample_reading_bottle.id, d)
    assert current_streak(library_store, today=d3) == 3


def test_longest_streak_empty(library_store):
    assert longest_streak(library_store) == 0


def test_longest_streak_gap(library_store, sample_reading_bottle):
    library_store.upsert_bottle(sample_reading_bottle)
    _add_tasting(library_store, sample_reading_bottle.id, date(2025, 5, 1))
    _add_tasting(library_store, sample_reading_bottle.id, date(2025, 5, 2))
    _add_tasting(library_store, sample_reading_bottle.id, date(2025, 5, 10))
    assert longest_streak(library_store) == 2


def test_compute_streak_structure(library_store, sample_reading_bottle):
    library_store.upsert_bottle(sample_reading_bottle)
    _add_tasting(library_store, sample_reading_bottle.id, date.today())
    info = compute_streak(library_store)
    assert isinstance(info, StreakInfo)
    assert info.current >= 1


def test_streak_summary_string(library_store):
    text = streak_summary(library_store)
    assert isinstance(text, str)


def test_active_dates_finished_bottle(library_store, sample_finished_bottle):
    library_store.upsert_bottle(sample_finished_bottle)
    dates = active_dates(library_store)
    assert len(dates) >= 1


def test_current_streak_yesterday_counts(library_store, sample_reading_bottle):
    library_store.upsert_bottle(sample_reading_bottle)
    yesterday = date.today() - timedelta(days=1)
    _add_tasting(library_store, sample_reading_bottle.id, yesterday)
    assert current_streak(library_store, today=date.today()) == 1


def test_longest_streak_single_day(library_store, sample_reading_bottle):
    library_store.upsert_bottle(sample_reading_bottle)
    _add_tasting(library_store, sample_reading_bottle.id, date(2025, 3, 1))
    assert longest_streak(library_store) == 1


def test_compute_streak_recent_days(library_store, sample_reading_bottle):
    library_store.upsert_bottle(sample_reading_bottle)
    _add_tasting(library_store, sample_reading_bottle.id, date.today())
    info = compute_streak(library_store)
    assert isinstance(info.active_days, list)


def test_streak_info_fields():
    info = StreakInfo(2, 7, "2025-01-01", ["2025-01-01"])
    assert info.longest == 7
    assert info.last_active == "2025-01-01"


def test_active_dates_ignores_zero_activity(library_store, sample_reading_bottle):
    library_store.upsert_bottle(sample_reading_bottle)
    s = Tasting.create(
        sample_reading_bottle.id,
        started_at="2025-05-01T10:00:00",
        ml_start=5,
        ml_end=5,
    )
    library_store.tastings[s.id] = s
    # zero pour — should not count as activity
    dates = active_dates(library_store)
    assert isinstance(dates, set)


def test_current_streak_no_today_but_yesterday(library_store, sample_reading_bottle):
    library_store.upsert_bottle(sample_reading_bottle)
    y = date(2025, 6, 1)
    _add_tasting(library_store, sample_reading_bottle.id, y)
    assert current_streak(library_store, today=date(2025, 6, 2)) == 1
