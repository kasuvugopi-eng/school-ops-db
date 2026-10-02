import pytest
from app.models.enums import SubmissionState
from app.services.submission_service import validate_submission_transition, SUBMISSION_TRANSITIONS

def test_valid_full_lifecycle():
    """NOT_STARTED -> IN_PROGRESS -> SUBMITTED -> COMPLETED"""
    assert validate_submission_transition(SubmissionState.NOT_STARTED, SubmissionState.IN_PROGRESS) == True
    assert validate_submission_transition(SubmissionState.IN_PROGRESS, SubmissionState.SUBMITTED) == True
    assert validate_submission_transition(SubmissionState.SUBMITTED, SubmissionState.COMPLETED) == True

def test_blocked_flow():
    """IN_PROGRESS -> BLOCKED -> IN_PROGRESS -> SUBMITTED"""
    assert validate_submission_transition(SubmissionState.IN_PROGRESS, SubmissionState.BLOCKED) == True
    assert validate_submission_transition(SubmissionState.BLOCKED, SubmissionState.IN_PROGRESS) == True

def test_revision_flow():
    """SUBMITTED -> REVISION_REQUESTED -> RESUBMITTED -> COMPLETED"""
    assert validate_submission_transition(SubmissionState.SUBMITTED, SubmissionState.REVISION_REQUESTED) == True
    assert validate_submission_transition(SubmissionState.REVISION_REQUESTED, SubmissionState.RESUBMITTED) == True
    assert validate_submission_transition(SubmissionState.RESUBMITTED, SubmissionState.COMPLETED) == True

def test_direct_submission():
    """NOT_STARTED -> SUBMITTED directly"""
    assert validate_submission_transition(SubmissionState.NOT_STARTED, SubmissionState.SUBMITTED) == True

def test_invalid_transitions():
    with pytest.raises(ValueError):
        validate_submission_transition(SubmissionState.COMPLETED, SubmissionState.SUBMITTED)
    with pytest.raises(ValueError):
        validate_submission_transition(SubmissionState.NOT_STARTED, SubmissionState.COMPLETED)
    with pytest.raises(ValueError):
        validate_submission_transition(SubmissionState.BLOCKED, SubmissionState.SUBMITTED)
    with pytest.raises(ValueError):
        validate_submission_transition(SubmissionState.SUBMITTED, SubmissionState.IN_PROGRESS)
