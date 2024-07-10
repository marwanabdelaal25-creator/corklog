"""Tests for corklog.errors."""

import pytest
from corklog.errors import (
    CorklogError,
    StorageError,
    ValidationError,
    NotFoundError,
    ImportError as PTImportError,
    ExportError,
    MigrationError,
    PluginError,
    ConflictError,
)


def test_corklog_error_defaults():
    exc = CorklogError("something broke")
    assert exc.message == "something broke"
    assert exc.code == "CORKLOG_ERROR"


def test_storage_error_code():
    exc = StorageError("disk full")
    assert exc.code == "STORAGE_ERROR"


def test_validation_error_without_field():
    exc = ValidationError("bad value")
    assert exc.field is None


def test_validation_error_with_field():
    exc = ValidationError("too short", field="title")
    assert "title" in str(exc)


def test_not_found_error_attrs():
    exc = NotFoundError("bottle", "abc-123")
    assert exc.entity == "bottle"
    assert exc.identifier == "abc-123"


def test_import_error_source():
    exc = PTImportError("cellartracker", "missing column")
    assert exc.source == "cellartracker"


def test_export_error_message():
    exc = ExportError("csv", "permission denied")
    assert "csv" in exc.message


def test_migration_error_formatting():
    exc = MigrationError(1, 3, "missing step")
    assert "1" in exc.message


def test_plugin_error_base():
    exc = PluginError("hook failed")
    assert isinstance(exc, CorklogError)


def test_conflict_error():
    exc = ConflictError("duplicate id")
    assert exc.code == "CONFLICT"


@pytest.mark.parametrize("cls", [
    StorageError, ValidationError, PTImportError,
    ExportError, MigrationError, PluginError, ConflictError,
])
def test_subclasses_are_corklog_errors(cls):
    assert issubclass(cls, CorklogError)


def test_not_found_raises():
    with pytest.raises(NotFoundError):
        raise NotFoundError("producer", "xyz")


def test_validation_inheritance():
    assert issubclass(ValidationError, CorklogError)


def test_storage_message_preserved():
    exc = StorageError("cannot read library file")
    assert "cannot read" in exc.message


def test_export_error_code():
    assert ExportError("md", "fail").code == "EXPORT_ERROR"


def test_migration_error_code():
    assert MigrationError(2, 3, "x").code == "MIGRATION_ERROR"


def test_corklog_str():
    assert str(CorklogError("hi")) == "hi"


def test_not_found_in_message():
    exc = NotFoundError("wishlist", "s1")
    assert "wishlist" in exc.message


def test_import_error_format():
    exc = PTImportError("csv", "bad row")
    assert "csv" in exc.message


def test_conflict_inheritance():
    assert issubclass(ConflictError, CorklogError)

from corklog.errors import format_error, is_not_found, wrap_os_error


def test_is_not_found_true():
    assert is_not_found(NotFoundError("bottle", "x")) is True


def test_is_not_found_false():
    assert is_not_found(ValueError("nope")) is False


def test_format_error_validation():
    exc = ValidationError("bad", field="title")
    assert "VALIDATION_ERROR" in format_error(exc)


def test_format_error_generic():
    exc = StorageError("disk")
    assert "STORAGE_ERROR" in format_error(exc)


def test_wrap_os_error():
    exc = wrap_os_error(OSError("errno"), "reading cellar file")
    assert isinstance(exc, StorageError)
