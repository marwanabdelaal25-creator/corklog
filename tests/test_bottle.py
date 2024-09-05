"""Tests for corklog.bottle."""

from datetime import date

import pytest

from corklog.bottle import Bottle, BottleCatalog, CellarStatus
from corklog.errors import ValidationError
from corklog.rating import Rating


def test_create_minimal():
    b = Bottle.create("Barolo")
    assert b.title == "Barolo"
    assert b.status == CellarStatus.CELLARED
    assert b.volume_ml == 750


def test_create_with_valid_lwin():
    b = Bottle.create("Margaux", lwin="1011266")
    assert b.lwin == "1011266"


def test_create_with_invalid_lwin_raises():
    with pytest.raises(ValidationError):
        Bottle.create("X", lwin="not-a-lwin")


def test_year_maps_to_vintage():
    b = Bottle.create("X", year=2015)
    assert b.vintage == 2015 and b.year == 2015


def test_empty_title_rejected():
    with pytest.raises(ValidationError):
        Bottle.create("  ")


def test_price_rounded():
    assert Bottle.create("X", price=12.999).price == 13.0


def test_progress_pct():
    b = Bottle.create("X", volume_ml=750, ml_poured=375)
    assert b.progress_pct() == 50.0


def test_progress_zero_when_no_volume():
    b = Bottle.create("X", volume_ml=0)
    assert b.progress_pct() == 0.0


def test_set_volume():
    b = Bottle.create("X")
    b.set_volume(200, 1500)
    assert b.volume_ml == 1500 and b.ml_poured == 200


def test_is_ready_in_window():
    b = Bottle.create("X", drink_from=2024, drink_to=2030)
    assert b.is_ready(2026) is True


def test_is_ready_no_window():
    assert Bottle.create("X").is_ready(2026) is True


def test_drink_window_too_young():
    b = Bottle.create("X", drink_from=2030, drink_to=2050)
    assert b.drink_window_status(2026) == "too young"


def test_drink_window_past_peak():
    b = Bottle.create("X", drink_from=2000, drink_to=2010)
    assert b.drink_window_status(2026) == "past peak"


def test_drink_window_ready():
    b = Bottle.create("X", drink_from=2020, drink_to=2030)
    assert b.drink_window_status(2026) == "ready"


def test_drink_window_unknown():
    assert Bottle.create("X").drink_window_status(2026) == "unknown"


def test_years_to_window():
    b = Bottle.create("X", drink_from=2030, drink_to=2050)
    assert b.years_to_window(2026) == 4


def test_years_to_window_ready_now():
    b = Bottle.create("X", drink_from=2020, drink_to=2030)
    assert b.years_to_window(2026) == 0


def test_mark_open():
    b = Bottle.create("X")
    b.mark_open(date(2025, 1, 1))
    assert b.status == CellarStatus.OPEN and b.started_at == "2025-01-01"


def test_mark_finished_empties_bottle():
    b = Bottle.create("X", volume_ml=750)
    b.mark_finished(date(2025, 1, 1))
    assert b.status == CellarStatus.DRUNK and b.ml_poured == 750


def test_mark_drunk_alias():
    b = Bottle.create("X")
    b.mark_drunk()
    assert b.status == CellarStatus.DRUNK


def test_cellar():
    b = Bottle.create("X", status=CellarStatus.WANT)
    b.cellar(date(2025, 2, 2))
    assert b.status == CellarStatus.CELLARED and b.acquired_at == "2025-02-02"


def test_dump():
    b = Bottle.create("X")
    b.dump(date(2025, 3, 3))
    assert b.status == CellarStatus.DUMPED


def test_set_status_from_string():
    b = Bottle.create("X")
    b.set_status("open")
    assert b.status == CellarStatus.OPEN


def test_short_label_with_vintage():
    assert Bottle.create("Margaux", year=2015).short_label() == "Margaux 2015"


def test_short_label_nv():
    assert Bottle.create("Champagne").short_label().endswith("NV")


def test_summary_line():
    line = Bottle.create("X", drink_from=2020, drink_to=2030).summary_line()
    assert "ready" in line


def test_rating_float():
    b = Bottle.create("X")
    b.rating = 4.5
    assert b.rating_value == 4.5
    assert isinstance(b.rating, Rating)


def test_rating_object():
    b = Bottle.create("X")
    b.rating = Rating.create(b.id, value=3.0)
    assert b.rating_value == 3.0


def test_to_from_dict_roundtrip():
    b = Bottle.create("Margaux", year=2015, varietal="Cab", price=650.0,
                      drink_from=2030, drink_to=2055, lwin="1011266")
    b.rating = 4.0
    b2 = Bottle.from_dict(b.to_dict())
    assert b2.title == "Margaux" and b2.vintage == 2015
    assert b2.varietal == "Cab" and b2.rating_value == 4.0 and b2.lwin == "1011266"


def test_matches():
    b = Bottle.create("Barolo", varietal="Nebbiolo", lwin="1011266")
    assert b.matches("nebbiolo")
    assert b.matches("1011266")
    assert not b.matches("merlot")


def test_matches_query_country():
    b = Bottle.create("X", country="Italy")
    assert b.matches_query("italy")


def test_is_active():
    assert Bottle.create("X", status=CellarStatus.OPEN).is_active()
    assert not Bottle.create("X", status=CellarStatus.DRUNK).is_active()


def test_days_open():
    b = Bottle.create("X")
    b.started_at = "2025-01-01"
    b.finished_at = "2025-01-08"
    assert b.days_open() == 7


def test_ml_remaining():
    assert Bottle.create("X", volume_ml=750, ml_poured=300).ml_remaining() == 450


def test_glasses_left():
    assert Bottle.create("X", volume_ml=750, ml_poured=0).glasses_left(150) == 5


def _cat():
    bottles = [
        Bottle.create("A", year=2015, varietal="Shiraz", status=CellarStatus.CELLARED,
                      drink_from=2024, drink_to=2030),
        Bottle.create("B", year=2019, varietal="Shiraz", status=CellarStatus.DRUNK),
        Bottle.create("C", year=2010, varietal="Merlot", status=CellarStatus.OPEN),
    ]
    bottles[1].finished_at = "2025-05-01"
    bottles[0].producer_ids = ["p1"]
    return BottleCatalog(bottles)


def test_catalog_by_status():
    assert len(_cat().by_status("cellared")) == 1


def test_catalog_by_producer():
    assert len(_cat().by_producer("p1")) == 1


def test_catalog_cellared_undrunk():
    cat = _cat()
    assert len(cat.cellared()) == 1
    assert len(cat.undrunk()) == 2


def test_catalog_ready_now():
    assert len(_cat().ready_now(2026)) == 1


def test_catalog_recently_finished():
    assert _cat().recently_finished()[0].title == "B"


def test_catalog_by_varietal():
    assert len(_cat().by_varietal("Shiraz")) == 2


def test_catalog_filter_vintage_range():
    assert len(_cat().filter_vintage_range(2014, 2020)) == 2


def test_catalog_group_and_summary():
    cat = _cat()
    assert isinstance(cat.group_by_status(), dict)
    assert "Cellar (3 bottles)" in cat.summary()


def test_catalog_sort_by_title():
    assert [b.title for b in _cat().sort_by_title()] == ["A", "B", "C"]
