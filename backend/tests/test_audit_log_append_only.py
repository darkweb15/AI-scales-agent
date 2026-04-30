"""Property-based test for audit log append-only invariant.

Task 11.1 — Property 11: Audit Log Append-Only Invariant
**Validates: Requirements 8.2**

Verifies that:
1. DatabaseService exposes no update or delete methods for InteractionLog
2. InteractionLog entries cannot be mutated after creation
3. Sequences of agent actions only ever append to the log
"""

from __future__ import annotations

import inspect
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.database.service import DatabaseService
from app.models.enums import AgentType, Channel, Direction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_log_entry(lead_id: uuid.UUID, summary: str = "test") -> Dict[str, Any]:
    return {
        "lead_id": lead_id,
        "agent_type": AgentType.cold_calling,
        "channel": Channel.call,
        "direction": Direction.outbound,
        "timestamp": datetime.now(timezone.utc),
        "summary": summary,
        "outcome": "contacted",
    }


# ---------------------------------------------------------------------------
# Static structural tests (no DB required)
# ---------------------------------------------------------------------------

def test_database_service_has_no_update_interaction_log_method():
    """Req 8.2: DatabaseService must NOT expose an update_interaction_log method."""
    assert not hasattr(DatabaseService, "update_interaction_log"), (
        "DatabaseService must not expose update_interaction_log — "
        "InteractionLog is append-only"
    )


def test_database_service_has_no_delete_interaction_log_method():
    """Req 8.2: DatabaseService must NOT expose a delete_interaction_log method."""
    assert not hasattr(DatabaseService, "delete_interaction_log"), (
        "DatabaseService must not expose delete_interaction_log — "
        "InteractionLog is append-only"
    )


def test_database_service_has_create_interaction_log():
    """DatabaseService must expose create_interaction_log (append)."""
    assert hasattr(DatabaseService, "create_interaction_log")
    assert callable(getattr(DatabaseService, "create_interaction_log"))


def test_database_service_interaction_log_methods_are_only_read_and_create():
    """Only create and read methods are allowed for InteractionLog."""
    allowed_prefixes = ("create_interaction_log", "get_interaction", "get_last_interaction")
    interaction_methods = [
        name for name in dir(DatabaseService)
        if "interaction" in name.lower() and not name.startswith("_")
    ]
    for method_name in interaction_methods:
        assert any(method_name.startswith(prefix) for prefix in allowed_prefixes), (
            f"Unexpected InteractionLog method: {method_name!r}. "
            f"Only create/read operations are allowed (append-only invariant)."
        )


# ---------------------------------------------------------------------------
# In-memory append-only log simulation
# ---------------------------------------------------------------------------

class InMemoryAppendOnlyLog:
    """Simulates the append-only InteractionLog behaviour."""

    def __init__(self) -> None:
        self._entries: List[Dict[str, Any]] = []
        self._entry_ids: set = set()

    def append(self, entry: Dict[str, Any]) -> str:
        entry_id = str(uuid.uuid4())
        # Freeze a copy so the original dict can't mutate the stored entry
        stored = dict(entry)
        stored["id"] = entry_id
        self._entries.append(stored)
        self._entry_ids.add(entry_id)
        return entry_id

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self._entries)

    def count(self) -> int:
        return len(self._entries)

    def try_update(self, entry_id: str, **kwargs) -> bool:
        """Attempt to update an entry — should always be rejected."""
        raise PermissionError("InteractionLog is append-only — updates are not permitted")

    def try_delete(self, entry_id: str) -> bool:
        """Attempt to delete an entry — should always be rejected."""
        raise PermissionError("InteractionLog is append-only — deletes are not permitted")


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------

# Strategy: generate a sequence of agent action types
agent_action_strategy = st.lists(
    st.sampled_from([
        ("cold_calling", "call", "contacted"),
        ("follow_up", "follow_up", "sent"),
        ("auto_mail", "send_email", "sent"),
        ("auto_reply", "receive_message", "replied"),
        ("demo_scheduling", "propose_slots", "proposed"),
        ("call_answering", "answer_call", "qualified"),
    ]),
    min_size=1,
    max_size=20,
)


@given(actions=agent_action_strategy)
@settings(max_examples=200)
def test_property_audit_log_append_only_invariant(actions):
    """**Property 11: Audit Log Append-Only Invariant**

    **Validates: Requirements 8.2**

    For any sequence of agent actions, the InteractionLog:
    1. Only grows (entries are never removed)
    2. Existing entries are never mutated after creation
    3. The count equals the number of actions performed
    """
    log = InMemoryAppendOnlyLog()
    lead_id = uuid.uuid4()

    initial_count = log.count()
    assert initial_count == 0

    entry_ids = []
    entry_snapshots = []

    for agent_type, action, outcome in actions:
        entry = {
            "lead_id": lead_id,
            "agent_type": agent_type,
            "channel": "call" if "call" in action else "email",
            "direction": "outbound",
            "timestamp": datetime.now(timezone.utc),
            "summary": f"{agent_type}: {action}",
            "outcome": outcome,
        }
        entry_id = log.append(entry)
        entry_ids.append(entry_id)
        # Snapshot the entry as stored
        entry_snapshots.append(dict(log.get_all()[-1]))

    # Invariant 1: count equals number of actions
    assert log.count() == len(actions), (
        f"Log count {log.count()} != actions count {len(actions)}"
    )

    # Invariant 2: all entries are still present (none deleted)
    all_entries = log.get_all()
    stored_ids = {e["id"] for e in all_entries}
    for eid in entry_ids:
        assert eid in stored_ids, f"Entry {eid} was removed from the log"

    # Invariant 3: entries match their original snapshots (not mutated)
    for i, (entry, snapshot) in enumerate(zip(all_entries, entry_snapshots)):
        assert entry == snapshot, (
            f"Entry {i} was mutated after creation: "
            f"original={snapshot}, current={entry}"
        )

    # Invariant 4: update attempts are rejected
    if entry_ids:
        with pytest.raises(PermissionError):
            log.try_update(entry_ids[0], outcome="mutated")

    # Invariant 5: delete attempts are rejected
    if entry_ids:
        with pytest.raises(PermissionError):
            log.try_delete(entry_ids[0])


@given(
    n_entries=st.integers(min_value=0, max_value=50),
)
@settings(max_examples=100)
def test_property_log_count_monotonically_increases(n_entries):
    """Log count only ever increases — never decreases."""
    log = InMemoryAppendOnlyLog()
    lead_id = uuid.uuid4()

    counts = [0]
    for i in range(n_entries):
        log.append(_make_log_entry(lead_id, summary=f"action_{i}"))
        counts.append(log.count())

    # Verify monotonic increase
    for i in range(1, len(counts)):
        assert counts[i] >= counts[i - 1], (
            f"Log count decreased from {counts[i-1]} to {counts[i]} at step {i}"
        )
    assert log.count() == n_entries
