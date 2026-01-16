#!/usr/bin/env python3
"""Import a (fake) CellarTracker export and print the resulting cellar."""
from __future__ import annotations

import tempfile
from pathlib import Path

from corklog.io_cellartracker import import_cellartracker
from corklog.reports import ReportBuilder
from corklog.storage import JsonStorage

EXPORT = """\
iWine,Wine,Vintage,Producer,Varietal,Country,Region,Quantity,Price,BeginConsume,EndConsume
1011266,Château Margaux,2015,Château Margaux,Cabernet Sauvignon,France,Bordeaux,3,650,2030,2055
2033444,Penfolds Grange,2016,Penfolds,Shiraz,Australia,South Australia,1,900,2026,2046
3099881,Sassicaia,2019,Tenuta San Guido,Cabernet Sauvignon,Italy,Tuscany,2,280,2027,2045
4055120,Cloudy Bay Sauvignon Blanc,2022,Cloudy Bay,Sauvignon Blanc,New Zealand,Marlborough,6,30,2023,2026
"""


def main() -> None:
    workdir = Path(tempfile.mkdtemp())
    export = workdir / "cellar_export.csv"
    export.write_text(EXPORT, encoding="utf-8")

    store = JsonStorage(workdir / "library.json")
    store.load()
    n = import_cellartracker(store, export)
    store.save()

    print("imported %d bottles from %s" % (n, export.name))
    print()
    print(ReportBuilder(store).status_report())


if __name__ == "__main__":
    main()
