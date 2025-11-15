"""Allow `python -m corklog` invocation."""

from corklog.cli import main

__doc__ = """
Entry point for the corklog CLI.

Examples:
  python -m corklog init
  python -m corklog bottle-add "Château Margaux" --producer "Château Margaux" --vintage 2015
  python -m corklog tasting-log <bottle-id> --pour 150 --score 4.5
  python -m corklog report tonight
  python -m corklog import cellar_export.csv --format cellartracker

Environment:
  CORKLOG_HOME  Directory for the default library.json (default: ~/.corklog/)
"""

if __name__ == "__main__":
    raise SystemExit(main())
