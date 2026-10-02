import pytest
from app.agents.extraction_schemas import DetectedIntent
from app.agents.intent_engine import ROLE_DENIED_INTENTS

def test_student_cannot_create_assignment():
    denied = ROLE_DENIED_INTENTS.get("student", set())
    assert "create_assignment" in denied
    assert "update_assignment" in denied
    assert "cancel_assignment" in denied
    assert "admin_config_change" in denied

def test_guardian_restrictions():
    denied = ROLE_DENIED_INTENTS.get("guardian", set())
    assert "submission" in denied
    assert "progress_update" in denied
    assert "create_assignment" in denied

def test_teacher_has_no_blanket_restrictions():
    denied = ROLE_DENIED_INTENTS.get("teacher", set())
    assert denied is None or len(denied) == 0

def test_admin_has_no_blanket_restrictions():
    denied = ROLE_DENIED_INTENTS.get("admin", set())
    assert denied is None or len(denied) == 0
