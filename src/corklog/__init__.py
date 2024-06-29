"""Corklog — a personal wine-cellar and tasting-notes manager by Marwan Helmy."""

from __future__ import annotations

__version__ = "1.2.0"
__author__ = "Marwan Helmy"
__email__ = "marwanabdelaal25@gmail.com"

from corklog.errors import (
    CorklogError,
    StorageError,
    ValidationError,
    NotFoundError,
    ImportError,
    ExportError,
    MigrationError,
    PluginError,
    ConflictError,
    format_error,
)
from corklog.storage import JsonStorage, LibraryStore, open_storage, LibraryFacade, SCHEMA_VERSION
from corklog.bottle import Bottle, CellarStatus, BottleCatalog
from corklog.producer import Producer, ProducerManager
from corklog.wishlist import Wishlist, WishlistManager
from corklog.tasting import Tasting, Session
from corklog.rating import Rating, RatingsManager
from corklog.tag import Tag
from corklog.goals import CellarGoal, Goal, GoalsManager
from corklog.collections import Collection, CollectionsManager
from corklog.quotes import Quote, QuotesManager
from corklog.notes import Note, NotesManager
from corklog.vertical import Vertical, VerticalManager
from corklog.regions import Region, RegionsManager
from corklog.recurring import RecurringRule, RecurringScheduler
from corklog.search import SearchEngine
from corklog.stats import compute_stats, LibraryStats, StatsReporter
from corklog.streaks import compute_streak, StreakInfo
from corklog.reports import ReportBuilder
from corklog.tags_manager import TagsManager
from corklog.audit_log import AuditLog
from corklog.plugins import PluginManager
from corklog.migrate import migrate_data, needs_migration, MigrationRunner
from corklog.backup import create_backup, restore_backup

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "CorklogError",
    "StorageError",
    "ValidationError",
    "NotFoundError",
    "ImportError",
    "ExportError",
    "MigrationError",
    "PluginError",
    "ConflictError",
    "format_error",
    "JsonStorage",
    "LibraryStore",
    "LibraryFacade",
    "open_storage",
    "SCHEMA_VERSION",
    "Bottle",
    "CellarStatus",
    "BottleCatalog",
    "Producer",
    "ProducerManager",
    "Wishlist",
    "WishlistManager",
    "Tasting",
    "Session",
    "Rating",
    "RatingsManager",
    "Tag",
    "CellarGoal",
    "Goal",
    "GoalsManager",
    "Collection",
    "CollectionsManager",
    "Quote",
    "QuotesManager",
    "Note",
    "NotesManager",
    "Vertical",
    "VerticalManager",
    "Region",
    "RegionsManager",
    "RecurringRule",
    "RecurringScheduler",
    "SearchEngine",
    "compute_stats",
    "LibraryStats",
    "StatsReporter",
    "compute_streak",
    "StreakInfo",
    "ReportBuilder",
    "TagsManager",
    "AuditLog",
    "PluginManager",
    "migrate_data",
    "needs_migration",
    "MigrationRunner",
    "create_backup",
    "restore_backup",
]
