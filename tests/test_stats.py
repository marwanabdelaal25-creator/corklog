"""Tests for corklog.stats."""

from datetime import date

import pytest

from corklog.bottle import Bottle, CellarStatus
from corklog.producer import Producer
from corklog.tasting import Tasting
from corklog.stats import (
    LibraryStats,
    StatsReporter,
    average_pour,
    average_price,
    average_rating_by_decade,
    avg_bottle_rating,
    bottles_finished_in_year,
    cellar_value,
    compare_years,
    compute_stats,
    completion_rate,
    count_by_status,
    decade_distribution,
    drink_window_distribution,
    dumped_rate,
    format_breakdown,
    format_leaderboard,
    format_stats,
    ml_by_month,
    monthly_pour,
    pour_by_weekday,
    pour_pace,
    pour_velocity,
    poured_ml_in_range,
    rating_distribution,
    ready_count,
    ready_to_drink,
    region_distribution,
    status_percentages,
    top_producers,
    top_tags,
    value_by_region,
    varietal_distribution,
)


def test_count_by_status_empty(json_storage):
    assert count_by_status(json_storage) == {}


def test_count_by_status(populated_json_storage):
    c = count_by_status(populated_json_storage)
    assert c.get("drunk", 0) == 1
    assert c.get("cellared", 0) == 1
    assert c.get("open", 0) == 1


def test_poured_ml_in_range(populated_json_storage):
    ml = poured_ml_in_range(populated_json_storage, date(2025, 1, 1), date(2025, 12, 31))
    assert ml == 200


def test_poured_ml_empty_range(json_storage):
    assert poured_ml_in_range(json_storage, date(2099, 1, 1), date(2099, 1, 31)) == 0


def test_avg_bottle_rating(populated_json_storage):
    avg = avg_bottle_rating(populated_json_storage)
    assert avg == 3.5


def test_avg_bottle_rating_empty(json_storage):
    assert avg_bottle_rating(json_storage) is None


def test_cellar_value(populated_json_storage):
    # margaux (cellared 650) + grange (open 900); drunk bottle excluded
    assert cellar_value(populated_json_storage) == 1550.0


def test_top_tags(populated_json_storage):
    tags = top_tags(populated_json_storage, n=5)
    assert ("first-growth", 1) in tags


def test_top_tags_empty(json_storage):
    assert top_tags(json_storage) == []


def test_pour_pace_keys(json_storage):
    pace = pour_pace(json_storage, days=7)
    assert pace["window_days"] == 7
    assert "ml" in pace and "ml_per_day" in pace


def test_pour_pace_zero_days(json_storage):
    assert pour_pace(json_storage, days=0)["ml_per_day"] == 0.0


def test_compute_stats(populated_json_storage):
    st = compute_stats(populated_json_storage)
    assert st.total_bottles == 3
    assert st.tastings_count == 1
    assert st.total_poured_ml == 200
    assert st.producers_count == 2
    assert st.cellar_value == 1550.0


def test_library_stats_summary_lines():
    st = LibraryStats(total_bottles=5, producers_count=2, tastings_count=3, avg_rating=4.1, cellar_value=99.5)
    lines = st.summary_lines()
    assert any("Bottles: 5" in ln for ln in lines)
    assert any("Cellar value" in ln for ln in lines)


def test_format_stats(populated_json_storage):
    text = format_stats(populated_json_storage)
    assert "Cellar stats" in text
    assert "Ready to drink" in text


def test_bottles_finished_in_year(populated_json_storage):
    assert bottles_finished_in_year(populated_json_storage, 2025) == 1


def test_bottles_finished_wrong_year(populated_json_storage):
    assert bottles_finished_in_year(populated_json_storage, 1990) == 0


def test_decade_distribution(populated_json_storage):
    dist = decade_distribution(populated_json_storage)
    assert dist["2010s"] == 2
    assert dist["2020s"] == 1


def test_decade_distribution_skips_missing_vintage(empty_storage):
    empty_storage.upsert_bottle(Bottle.create("NV Champagne"))
    assert decade_distribution(empty_storage) == {}


def test_region_distribution_by_country(populated_json_storage):
    dist = region_distribution(populated_json_storage)
    assert dist.get("Australia") == 2
    assert dist.get("France") == 1


def test_varietal_distribution(populated_json_storage):
    dist = varietal_distribution(populated_json_storage)
    assert dist.get("Shiraz") == 2
    assert dist.get("Cabernet Sauvignon") == 1


def test_top_producers(populated_json_storage):
    top = top_producers(populated_json_storage, 3)
    assert top[0] == ("Penfolds", 2)


def test_ready_to_drink(empty_storage):
    ready = Bottle.create("Drink Me", vintage=2018, drink_from=2024, drink_to=2030,
                          status=CellarStatus.CELLARED)
    young = Bottle.create("Hold Me", vintage=2021, drink_from=2030, drink_to=2050,
                          status=CellarStatus.CELLARED)
    empty_storage.upsert_bottle(ready)
    empty_storage.upsert_bottle(young)
    got = ready_to_drink(empty_storage, 2026)
    assert [b.title for b in got] == ["Drink Me"]
    assert ready_count(empty_storage, 2026) == 1


def test_drink_window_distribution(populated_json_storage):
    dist = drink_window_distribution(populated_json_storage, 2026)
    assert dist.get("too young") == 1   # margaux (from 2030)
    assert dist.get("ready") == 1       # grange (open, 2026-2046)


def test_average_rating_by_decade(populated_json_storage):
    avg = average_rating_by_decade(populated_json_storage)
    assert avg["2020s"] == 3.5


def test_value_by_region(populated_json_storage):
    val = value_by_region(populated_json_storage)
    assert val.get("Australia") == 915.0
    assert val.get("France") == 650.0


def test_format_breakdown(populated_storage):
    out = format_breakdown(populated_storage)
    assert "Detailed stats" in out
    assert "By vintage decade:" in out
    assert "By region:" in out
    assert "Top producers:" in out


def test_monthly_pour(populated_storage):
    assert monthly_pour(populated_storage, 2025, 3) == 200


def test_ml_by_month(populated_storage):
    assert ml_by_month(populated_storage, 2025) == {3: 200}


def test_status_percentages(populated_storage):
    pcts = status_percentages(populated_storage)
    assert abs(sum(pcts.values()) - 100.0) < 0.5


def test_average_price(populated_storage):
    # (650 + 900 + 15) / 3
    assert average_price(populated_storage) == pytest.approx(521.67, abs=0.01)


def test_average_price_empty(empty_storage):
    assert average_price(empty_storage) is None


def test_pour_by_weekday(populated_storage):
    by = pour_by_weekday(populated_storage)
    assert len(by) == 7
    assert by[5] == 200  # 2025-03-15 is a Saturday


def test_completion_rate(populated_storage):
    assert completion_rate(populated_storage) == pytest.approx(33.3, abs=0.1)


def test_completion_rate_empty(empty_storage):
    assert completion_rate(empty_storage) == 0.0


def test_dumped_rate_empty(empty_storage):
    assert dumped_rate(empty_storage) == 0.0


def test_dumped_rate(empty_storage, bottles_batch):
    for b in bottles_batch:
        empty_storage.upsert_bottle(b)
    assert dumped_rate(empty_storage) == 20.0


def test_average_pour(populated_storage):
    assert average_pour(populated_storage) == 200.0


def test_average_pour_empty(empty_storage):
    assert average_pour(empty_storage) is None


def test_rating_distribution(populated_storage):
    assert isinstance(rating_distribution(populated_storage), dict)


def test_format_leaderboard_scored(empty_storage, sample_bottle):
    sample_bottle.rating_value = 4.5
    empty_storage.upsert_bottle(sample_bottle)
    assert "Top scored" in format_leaderboard(empty_storage)


def test_format_leaderboard_empty(empty_storage):
    assert "No scored" in format_leaderboard(empty_storage)


def test_pour_velocity(populated_storage):
    assert pour_velocity(populated_storage) >= 0


def test_compare_years(populated_storage):
    assert "2024" in compare_years(populated_storage, 2024, 2025)


def test_reporter_full(populated_storage):
    assert "Detailed" in StatsReporter(populated_storage).full_report()


def test_reporter_quick(populated_storage):
    assert "Cellar stats" in StatsReporter(populated_storage).quick()


def test_reporter_export_json(populated_storage):
    data = StatsReporter(populated_storage).export_json_summary()
    assert "completion_rate" in data and "cellar_value" in data


def test_reporter_entity_counts(populated_storage):
    assert isinstance(StatsReporter(populated_storage).entity_counts(), dict)


def test_reporter_monthly_table(populated_storage):
    assert "2025" in StatsReporter(populated_storage).monthly_table(2025)


def test_reporter_weekday_chart(populated_storage):
    assert "Mon" in StatsReporter(populated_storage).weekday_chart()


def test_reporter_decade_chart(populated_storage):
    assert "2010s" in StatsReporter(populated_storage).decade_chart()


def test_reporter_decade_chart_empty(empty_storage):
    assert "No vintages" in StatsReporter(empty_storage).decade_chart()


def test_reporter_region_chart(populated_storage):
    assert "Australia" in StatsReporter(populated_storage).region_chart()


def test_reporter_region_chart_empty(empty_storage):
    assert "No regions" in StatsReporter(empty_storage).region_chart()
