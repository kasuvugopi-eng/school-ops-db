# ADR-003: State Machine Enforcement in Service Layer

## Status
**Accepted** — October 2026

## Context
Assignments and submissions go through well-defined lifecycle states. Invalid state transitions (e.g., a cancelled assignment suddenly becoming active, or a completed submission being re-submitted) could corrupt business data and confuse users.

The question is where to enforce state transition rules:
1. **Database layer** (CHECK constraints, triggers)
2. **Service layer** (application code)
3. **API layer** (route handlers)

## Decision
**State transitions are enforced in the service layer using explicit transition maps.**

### Implementation

```python
# Explicit allowed transitions
ASSIGNMENT_TRANSITIONS = {
    AssignmentState.DRAFT: {AssignmentState.ACTIVE, AssignmentState.PENDING_APPROVAL},
    AssignmentState.PENDING_APPROVAL: {AssignmentState.ACTIVE, AssignmentState.DRAFT},
    AssignmentState.ACTIVE: {AssignmentState.COMPLETED, AssignmentState.CANCELLED},
    # COMPLETED and CANCELLED are terminal — no outgoing transitions
}

SUBMISSION_TRANSITIONS = {
    SubmissionState.NOT_STARTED: {SubmissionState.IN_PROGRESS, SubmissionState.SUBMITTED},
    SubmissionState.IN_PROGRESS: {SubmissionState.BLOCKED, SubmissionState.SUBMITTED},
    SubmissionState.BLOCKED: {SubmissionState.IN_PROGRESS},
    SubmissionState.SUBMITTED: {SubmissionState.REVISION_REQUESTED, SubmissionState.COMPLETED},
    SubmissionState.REVISION_REQUESTED: {SubmissionState.RESUBMITTED},
    SubmissionState.RESUBMITTED: {SubmissionState.COMPLETED, SubmissionState.REVISION_REQUESTED},
    # COMPLETED is terminal
}

def validate_assignment_transition(current, target):
    allowed = ASSIGNMENT_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(f"Invalid transition: {current} → {target}")
    return True
```

### Why service layer, not database?
- **Expressiveness**: PostgreSQL CHECK constraints can validate individual column values but cannot express "only allow state X if previous state was Y". Triggers could do it but are harder to test and debug.
- **Testability**: Python functions with explicit transition maps are trivially unit-testable (see `test_assignment_states.py` and `test_submission_states.py`).
- **Readability**: A junior engineer can read the transition map and understand the business rules instantly.
- **Flexibility**: Adding a new state or transition is a one-line change in the map.

### Guard rail: All state changes MUST go through the service layer
Direct database updates (`UPDATE submissions SET state = ...`) bypass the state machine. Application code should never update state directly.

## Consequences
### Positive
- State transitions are explicit, documented, and exhaustively tested.
- Easy for a junior engineer to understand and extend.
- State machine is a single source of truth.

### Negative
- If someone bypasses the service layer (e.g., admin SQL query), the state machine is not enforced.
- The database alone cannot prevent invalid states — relies on application discipline.

## Mitigation
- The audit service logs every state change with the previous and new state, making invalid transitions detectable.
- Future enhancement: add a PostgreSQL trigger as a secondary guard rail.
