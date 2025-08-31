"""Tests for corklog.audit_log."""

import pytest
from corklog.audit_log import AuditLog, AuditEntry


def test_audit_entry_record():
    e = AuditEntry.record("create", "bottle", "b1", {"title": "T"})
    assert e.action == "create"
    assert e.entity_type == "bottle"
    assert e.timestamp


def test_audit_log_append(json_storage):
    log = AuditLog(json_storage)
    log.append(AuditEntry.record("update", "bottle", "b1"))
    assert len(log.recent(limit=10)) >= 1


def test_log_create(json_storage):
    log = AuditLog(json_storage)
    log.log_create("bottle", "b1", title="X")
    recent = log.recent(1)
    assert recent[0].action == "create"


def test_log_update(json_storage):
    log = AuditLog(json_storage)
    log.log_update("producer", "a1", name="Y")
    assert log.recent(1)[0].entity_type == "producer"


def test_log_delete(json_storage):
    log = AuditLog(json_storage)
    log.log_delete("wishlist", "s1")
    assert log.recent(1)[0].action == "delete"


def test_recent_order(json_storage):
    log = AuditLog(json_storage)
    log.log_create("bottle", "1")
    log.log_create("bottle", "2")
    recent = log.recent(2)
    assert recent[0].entity_id == "2"


def test_for_entity(json_storage):
    log = AuditLog(json_storage)
    log.log_update("bottle", "target", x=1)
    log.log_update("bottle", "other", x=2)
    rows = log.for_entity("bottle", "target")
    assert len(rows) == 1
    assert rows[0].entity_id == "target"


def test_max_entries_trim(json_storage):
    log = AuditLog(json_storage, max_entries=3)
    for i in range(5):
        log.log_create("bottle", str(i))
    stored = json_storage.raw_get("audit")
    assert len(stored) <= 3


def test_entry_to_dict():
    e = AuditEntry.record("x", "y", "z")
    d = e.to_dict()
    assert d["entity_id"] == "z"


def test_default_user(json_storage):
    AuditLog(json_storage).log_create("bottle", "b")
    assert log_recent_user(json_storage) == "local"


def log_recent_user(json_storage):
    return AuditLog(json_storage).recent(1)[0].user


def test_details_preserved(json_storage):
    log = AuditLog(json_storage)
    log.log_create("bottle", "b1", minutes=300)
    details = log.recent(1)[0].details
    assert details.get("minutes") == 300


def test_empty_recent(json_storage):
    assert AuditLog(json_storage).recent() == []


def test_for_entity_empty(json_storage):
    assert AuditLog(json_storage).for_entity("bottle", "nope") == []


def test_multiple_entity_types(json_storage):
    log = AuditLog(json_storage)
    log.log_create("bottle", "b")
    log.log_create("producer", "a")
    assert len(log.recent(10)) == 2


def test_entry_id_unique(json_storage):
    log = AuditLog(json_storage)
    log.log_create("bottle", "1")
    log.log_create("bottle", "2")
    ids = {e.id for e in log.recent(2)}
    assert len(ids) == 2


def test_audit_persists_in_storage(json_storage):
    AuditLog(json_storage).log_delete("tag", "t1")
    assert len(json_storage.raw_get("audit")) == 1


def test_record_defaults_details_empty():
    e = AuditEntry.record("a", "b", "c")
    assert e.details == {}


def test_recent_limit_respected(json_storage):
    log = AuditLog(json_storage)
    for i in range(20):
        log.log_create("bottle", str(i))
    assert len(log.recent(limit=5)) == 5
