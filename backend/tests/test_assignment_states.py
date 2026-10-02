import pytest
from app.models.enums import AssignmentState
from app.services.assignment_service import validate_assignment_transition, ASSIGNMENT_TRANSITIONS

def test_valid_transitions():
    assert validate_assignment_transition(AssignmentState.DRAFT, AssignmentState.ACTIVE) == True
    assert validate_assignment_transition(AssignmentState.DRAFT, AssignmentState.PENDING_APPROVAL) == True
    assert validate_assignment_transition(AssignmentState.PENDING_APPROVAL, AssignmentState.ACTIVE) == True
    assert validate_assignment_transition(AssignmentState.PENDING_APPROVAL, AssignmentState.DRAFT) == True
    assert validate_assignment_transition(AssignmentState.ACTIVE, AssignmentState.COMPLETED) == True
    assert validate_assignment_transition(AssignmentState.ACTIVE, AssignmentState.CANCELLED) == True

def test_invalid_transitions():
    with pytest.raises(ValueError):
        validate_assignment_transition(AssignmentState.CANCELLED, AssignmentState.ACTIVE)
    with pytest.raises(ValueError):
        validate_assignment_transition(AssignmentState.COMPLETED, AssignmentState.ACTIVE)
    with pytest.raises(ValueError):
        validate_assignment_transition(AssignmentState.DRAFT, AssignmentState.COMPLETED)
    with pytest.raises(ValueError):
        validate_assignment_transition(AssignmentState.DRAFT, AssignmentState.CANCELLED)

def test_all_states_covered():
    """Ensure all non-terminal states have defined transitions."""
    non_terminal = {AssignmentState.DRAFT, AssignmentState.PENDING_APPROVAL, AssignmentState.ACTIVE}
    for state in non_terminal:
        assert state in ASSIGNMENT_TRANSITIONS
        assert len(ASSIGNMENT_TRANSITIONS[state]) > 0

def test_terminal_states_have_no_transitions():
    """COMPLETED and CANCELLED should have no outgoing transitions."""
    terminal = {AssignmentState.COMPLETED, AssignmentState.CANCELLED}
    for state in terminal:
        assert state not in ASSIGNMENT_TRANSITIONS or len(ASSIGNMENT_TRANSITIONS.get(state, set())) == 0
