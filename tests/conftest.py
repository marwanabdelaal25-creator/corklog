"""Shared pytest fixtures for corklog."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from corklog.producer import Producer
from corklog.bottle import Bottle, CellarStatus
from corklog.rating import Rating
from corklog.tasting import Tasting
from corklog.wishlist import Wishlist
from corklog.storage import JsonStorage, LibraryStore, SCHEMA_VERSION
from corklog.tag import Tag

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_LIBRARY = FIXTURES / "sample_library.json"
CELLARTRACKER_FIXTURE = (
    FIXTURES / "imports" / "cellartracker" / "2025" / "cellartracker_2025_01.csv"
)

LWIN7 = "1011266"          # the wine
LWIN11 = "10112662015"     # wine + vintage
LWIN_ALT = "1234567"


@pytest.fixture
def tmp_library_path(tmp_path):
    return tmp_path / "library.json"


@pytest.fixture
def empty_storage(tmp_library_path):
    st = JsonStorage(tmp_library_path)
    st.load()
    return st


@pytest.fixture
def storage(empty_storage):
    return empty_storage


@pytest.fixture
def library_store(empty_storage):
    return empty_storage


@pytest.fixture
def json_storage(empty_storage):
    return empty_storage


@pytest.fixture
def audit_dir(tmp_path):
    return tmp_path


@pytest.fixture
def populated_storage(empty_storage):
    from corklog.goals import CellarGoal

    margaux = Producer.create("Château Margaux", id="prod-margaux")
    penfolds = Producer.create("Penfolds", id="prod-penfolds")
    empty_storage.upsert_producer(margaux)
    empty_storage.upsert_producer(penfolds)

    tag = Tag.create("first-growth", id="tag-001")
    empty_storage.upsert_tag(tag)
    wishlist = Wishlist(name="to-buy", id="wishlist-001")
    empty_storage.upsert_wishlist(wishlist)

    margaux2015 = Bottle.create(
        "Château Margaux",
        id="b-margaux15",
        lwin=LWIN7,
        vintage=2015,
        varietal="Cabernet Sauvignon",
        country="France",
        price=650.0,
        drink_from=2030,
        drink_to=2055,
        status=CellarStatus.CELLARED,
    )
    margaux2015.producer_ids = [margaux.id]
    margaux2015.tag_ids = ["tag-001"]
    margaux2015.wishlist_ids = ["wishlist-001"]

    grange = Bottle.create(
        "Penfolds Grange",
        id="b-grange16",
        vintage=2016,
        varietal="Shiraz",
        country="Australia",
        price=900.0,
        drink_from=2026,
        drink_to=2046,
        status=CellarStatus.OPEN,
        ml_poured=200,
    )
    grange.producer_ids = [penfolds.id]
    grange.started_at = "2025-03-15"

    everyday = Bottle.create(
        "Koonunga Hill Shiraz",
        id="b-everyday21",
        vintage=2021,
        varietal="Shiraz",
        country="Australia",
        price=15.0,
        status=CellarStatus.DRUNK,
        ml_poured=750,
    )
    everyday.producer_ids = [penfolds.id]
    everyday.finished_at = "2025-06-15"
    everyday.rating = 3.5

    for b in (margaux2015, grange, everyday):
        empty_storage.upsert_bottle(b)

    tasting = Tasting.create(
        grange.id,
        ml_start=0,
        ml_end=200,
        score=4.5,
        occasion="Sunday roast",
        started_at="2025-03-15T20:00:00",
    )
    empty_storage.add_tasting(tasting)
    empty_storage.save_goals([CellarGoal.create("Drink 24 in 2026", "bottles", 24, "year")])
    return empty_storage


@pytest.fixture
def sample_library_dict(populated_storage):
    return populated_storage.snapshot()


@pytest.fixture
def populated_json_storage(populated_storage):
    return populated_storage


@pytest.fixture
def populated_library_store(populated_storage):
    return populated_storage


@pytest.fixture
def lwin_id():
    return LWIN7


@pytest.fixture
def lwin11_id():
    return LWIN11


@pytest.fixture
def lwin_id_alt():
    return LWIN_ALT


@pytest.fixture
def sample_bottle():
    return Bottle.create(
        "Barolo Brunate",
        id="bottle-test-1",
        vintage=2018,
        varietal="Nebbiolo",
        country="Italy",
        price=80.0,
        drink_from=2026,
        drink_to=2040,
        status=CellarStatus.OPEN,
        ml_poured=150,
    )


@pytest.fixture
def sample_read_bottle():
    bk = Bottle.create(
        "Sancerre Les Monts Damnés",
        id="bottle-read-1",
        vintage=2022,
        varietal="Sauvignon Blanc",
        country="France",
        status=CellarStatus.DRUNK,
        ml_poured=750,
    )
    bk.finished_at = "2025-06-15"
    return bk


@pytest.fixture
def sample_reading_bottle(sample_bottle):
    return sample_bottle


@pytest.fixture
def sample_finished_bottle(sample_read_bottle):
    return sample_read_bottle


@pytest.fixture
def sample_producer():
    return Producer.create("Domaine de la Romanée-Conti", id="prod-drc", email="contact@drc.example")


@pytest.fixture
def sample_tag():
    return Tag.create("burgundy", id="tag-burg", color="#7b1e3a")


@pytest.fixture
def sample_wishlist():
    return Wishlist(name="to-buy", id="wl-fav")


@pytest.fixture
def sample_tasting(sample_bottle):
    return Tasting.create(
        sample_bottle.id,
        id="tasting-fixture",
        ml_start=0,
        ml_end=150,
        score=4.0,
        occasion="weeknight",
        started_at="2026-05-01T19:00:00",
    )


@pytest.fixture
def sample_rating(sample_bottle):
    return Rating.create(sample_bottle.id, value=4.0, review="Tarry, still tight")


@pytest.fixture
def storage_with_bottle(empty_storage, sample_bottle, sample_producer):
    empty_storage.upsert_producer(sample_producer)
    sample_bottle.producer_ids = [sample_producer.id]
    empty_storage.upsert_bottle(sample_bottle)
    return empty_storage


@pytest.fixture
def bottles_batch():
    rows = [
        ("Chablis Premier Cru", CellarStatus.CELLARED),
        ("Châteauneuf-du-Pape", CellarStatus.OPEN),
        ("Rioja Gran Reserva", CellarStatus.DRUNK),
        ("Corked Merlot", CellarStatus.DUMPED),
        ("Champagne Brut NV", CellarStatus.WANT),
    ]
    out = []
    for title, st in rows:
        b = Bottle.create(title, status=st)
        if st == CellarStatus.DRUNK:
            b.mark_finished(date(2025, 1, 15))
        out.append(b)
    return out


@pytest.fixture
def mini_csv(tmp_path):
    p = tmp_path / "bottles.csv"
    p.write_text(
        "title,producer,lwin,vintage,region,varietal,price,status,rating,tags\n"
        '"Château Margaux","Château Margaux",1011266,2015,Bordeaux,Cabernet Sauvignon,650,cellared,,first-growth\n'
        '"Cloudy Bay Sauvignon Blanc","Cloudy Bay",,2022,Marlborough,Sauvignon Blanc,30,drunk,4,white\n',
        encoding="utf-8",
    )
    return p


@pytest.fixture
def cellartracker_csv():
    if CELLARTRACKER_FIXTURE.exists():
        return CELLARTRACKER_FIXTURE
    pytest.skip("cellartracker fixture file not present")


@pytest.fixture
def cellartracker_csv_tmp(tmp_path):
    p = tmp_path / "cellartracker.csv"
    p.write_text(
        "iWine,Wine,Vintage,Producer,Varietal,Country,Region,Quantity,Price,BeginConsume,EndConsume\n"
        "1011266,Château Margaux,2015,Château Margaux,Cabernet Sauvignon,France,Bordeaux,3,650,2030,2055\n"
        "2033444,Penfolds Grange,2016,Penfolds,Shiraz,Australia,South Australia,1,900,2026,2046\n",
        encoding="utf-8-sig",
    )
    return p


@pytest.fixture
def vivino_csv(tmp_path):
    p = tmp_path / "vivino.csv"
    p.write_text(
        "Winery,Wine name,Vintage,Region,Country,Your rating,Scan date\n"
        "Cloudy Bay,Sauvignon Blanc,2022,Marlborough,New Zealand,4.5,2024-02-01\n"
        "Tignanello,Tignanello,2019,Tuscany,Italy,4.0,2024-02-08\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def lib(tmp_path):
    p = tmp_path / "library.json"
    st = JsonStorage(p)
    st.load()
    return p


def make_bottle(title: str, **kw) -> Bottle:
    return Bottle.create(title, **kw)


def seed_tastings(store: JsonStorage, bottle_id: str, days: list[date]) -> None:
    for i, d in enumerate(days):
        sess = Tasting.create(
            bottle_id,
            ml_start=i * 75,
            ml_end=(i + 1) * 75,
            score=4.0,
            started_at=d.isoformat() + "T20:00:00",
        )
        store.add_tasting(sess)
