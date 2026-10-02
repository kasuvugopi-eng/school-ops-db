from app.websocket.manager import ws_manager

async def emit_submission_update(school_id: str, data: dict):
    await ws_manager.broadcast_to_school(str(school_id), {
        "type": "SUBMISSION_UPDATED",
        "data": data
    })

async def emit_student_blocked(school_id: str, data: dict):
    await ws_manager.broadcast_to_school(str(school_id), {
        "type": "STUDENT_BLOCKED",
        "data": data
    })

async def emit_assignment_created(school_id: str, data: dict):
    await ws_manager.broadcast_to_school(str(school_id), {
        "type": "ASSIGNMENT_CREATED",
        "data": data
    })

async def emit_parse_ready(school_id: str, data: dict):
    await ws_manager.broadcast_to_school(str(school_id), {
        "type": "PARSE_READY",
        "data": data
    })

async def emit_feedback_given(school_id: str, data: dict):
    await ws_manager.broadcast_to_school(str(school_id), {
        "type": "FEEDBACK_GIVEN",
        "data": data
    })
