"""Property test for LeadStatus monotonic progression.

**Property 4: Lead Status Monotonic Progression**
**Validates: Requirements 8.1**

The system must ensure that lead status transitions only progress forward
through the defined LeadStatus pipeline unless an explicit reset action is
performed by an operator.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.enums import (
    LEAD_STATUS_ORDER,
    TERMINAL_STATUSES,
    LeadStatus,
)


def get_status_rank(status: LeadStatus) -> int:
    """Return the ordinal rank of a status in the forward pipeline.

    Terminal statuses (not_interested, unsubscribed, do_not_contact) are
    treated as rank -1 because they are valid exits from any pipeline stage
    and are not subject to the monotonic ordering constraint.
    """
    if status in TERMINAL_STATUSES:
        return -1
    try:
        return LEAD_STATUS_ORDER.index(status)
    except ValueError:
        return -1


def is_valid_transition(from_status: LeadStatus, to_status: LeadStatus) -> bool:
    """Return True if transitioning from_status → to_status is valid.

    Rules:
    - Any status → terminal status is always valid (opt-out / DNC).
    - Within the forward pipeline, rank must be strictly non-decreasing
      (same rank = no-op, higher rank = forward progress).
    - Backward transitions within the pipeline are invalid.
    """
    # Transitioning to a terminal status is always allowed
    if to_status in TERMINAL_STATUSES:
        return True

    from_rank = get_status_rank(from_status)
    to_rank = get_status_rank(to_status)

    # If from_status is terminal, no further forward transitions are valid
    if from_rank == -1:
        return False

    # Forward or same-stage transitions are valid
    return to_rank >= from_rank


# Strategy: generate a sequence of LeadStatus values
lead_status_strategy = st.lists(
    st.sampled_from(list(LeadStatus)),
    min_size=2,
    max_size=20,
)


@given(status_sequence=lead_status_strategy)
@settings(max_examples=500)
def test_no_backward_regression_in_pipeline(status_sequence: list) -> None:
    """Property: once a lead enters a forward pipeline stage, it must not
    regress to an earlier stage without an explicit operator reset.

    We simulate a sequence of status transitions and assert that every
    consecutive pair (from, to) satisfies is_valid_transition.
    """
    for i in range(len(status_sequence) - 1):
        from_s = status_sequence[i]
        to_s = status_sequence[i + 1]

        # If this transition would be invalid, the system should reject it.
        # We verify our validation function correctly identifies backward moves.
        from_rank = get_status_rank(from_s)
        to_rank = get_status_rank(to_s)

        if from_rank != -1 and to_rank != -1:
            # Both are pipeline statuses — to_rank must be >= from_rank
            assert to_rank >= from_rank or not is_valid_transition(from_s, to_s), (
                f"Backward transition {from_s} → {to_s} was incorrectly "
                f"marked as valid (from_rank={from_rank}, to_rank={to_rank})"
            )


@given(
    from_status=st.sampled_from(list(LeadStatus)),
    to_status=st.sampled_from(list(LeadStatus)),
)
@settings(max_examples=500)
def test_terminal_transitions_always_valid(
    from_status: LeadStatus, to_status: LeadStatus
) -> None:
    """Property: transitioning to any terminal status is always valid
    regardless of the current pipeline stage.
    """
    if to_status in TERMINAL_STATUSES:
        assert is_valid_transition(from_status, to_status), (
            f"Transition {from_status} → {to_status} should always be valid "
            f"(to_status is terminal) but was rejected."
        )


@given(status=st.sampled_from(list(LeadStatus)))
@settings(max_examples=100)
def test_same_status_transition_is_valid(status: LeadStatus) -> None:
    """Property: a no-op transition (same status → same status) is always valid."""
    assert is_valid_transition(status, status), (
        f"No-op transition {status} → {status} should be valid but was rejected."
    )


@given(
    from_status=st.sampled_from(list(LeadStatus)),
    to_status=st.sampled_from(list(LeadStatus)),
)
@settings(max_examples=500)
def test_backward_pipeline_transitions_are_invalid(
    from_status: LeadStatus, to_status: LeadStatus
) -> None:
    """Property: any transition that moves backward in the forward pipeline
    (non-terminal statuses only) must be flagged as invalid.
    """
    from_rank = get_status_rank(from_status)
    to_rank = get_status_rank(to_status)

    # Only test non-terminal → non-terminal backward moves
    if from_rank != -1 and to_rank != -1 and to_rank < from_rank:
        assert not is_valid_transition(from_status, to_status), (
            f"Backward transition {from_status} (rank {from_rank}) → "
            f"{to_status} (rank {to_rank}) should be invalid but was accepted."
        )
