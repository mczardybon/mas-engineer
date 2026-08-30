"""
test_r110308_mq_iso_migrate.py — R110-308: cover _parse_iso and _migrate in
dev_message_queue that existing tests don't exercise.

Specifically these lines were uncovered:
  - _parse_iso L130-133: try/except for invalid ISO strings
  - _migrate L142-148: schema version branching
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.resolve()
TOOLS = REPO_ROOT / "tools"


@pytest.fixture
def mq():
    """Import dev_message_queue as 'mq' module."""
    sys.path.insert(0, str(TOOLS))
    try:
        import dev_message_queue
        yield dev_message_queue
    finally:
        sys.path.pop(0)


def test_parse_iso_none_input(mq):
    """_parse_iso(None) returns None via the 'not s' guard (L128-129)."""
    assert mq._parse_iso(None) is None


def test_parse_iso_empty_string(mq):
    """_parse_iso('') returns None via the 'not s' guard."""
    assert mq._parse_iso("") is None


def test_parse_iso_valid_utc_zulu(mq):
    """_parse_iso('2026-08-30T12:00:00Z') parses correctly to a datetime."""
    result = mq._parse_iso("2026-08-30T12:00:00Z")
    assert isinstance(result, datetime)
    assert result.year == 2026
    assert result.month == 8
    assert result.day == 30
    assert result.tzinfo is not None


def test_parse_iso_valid_with_offset(mq):
    """_parse_iso('2026-08-30T12:00:00+00:00') parses correctly."""
    result = mq._parse_iso("2026-08-30T12:00:00+00:00")
    assert isinstance(result, datetime)
    assert result.tzinfo is not None


def test_parse_iso_invalid_garbage_returns_none(mq):
    """_parse_iso('not-a-date') returns None via the except branch (L130-133)."""
    result = mq._parse_iso("not-a-date")
    assert result is None


def test_parse_iso_partial_invalid_returns_none(mq):
    """_parse_iso('2026-99-99T99:99:99') returns None via ValueError."""
    result = mq._parse_iso("2026-99-99T99:99:99")
    assert result is None


def test_migrate_v1_is_noop(mq):
    """_migrate for schema_version=1 returns the message unchanged."""
    msg = {"schema_version": 1, "name": "test", "payload": "x"}
    result = mq._migrate(msg)
    assert result is msg  # same object (no copy)


def test_migrate_default_version_is_v1(mq):
    """_migrate on a message without schema_version defaults to v1 → no-op."""
    msg = {"name": "test"}  # no schema_version key
    result = mq._migrate(msg)
    assert result is msg


def test_migrate_older_version_returns_unchanged(mq):
    """_migrate for schema_version < current (e.g. 0) is a no-op (L145-147)."""
    msg = {"schema_version": 0, "name": "legacy"}
    result = mq._migrate(msg)
    assert result is msg


def test_migrate_future_unknown_version_returns_unchanged(mq):
    """_migrate for schema_version > current (e.g. 999) is a no-op (L148)."""
    msg = {"schema_version": 999, "name": "future"}
    result = mq._migrate(msg)
    assert result is msg
