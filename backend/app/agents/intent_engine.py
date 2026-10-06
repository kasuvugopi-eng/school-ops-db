from openai import OpenAI
from app.config import settings
from app.agents.extraction_schemas import DetectedIntent
from app.agents.prompts import INTENT_CLASSIFICATION_PROMPT

VALID_INTENTS = [
    "create_assignment", "update_assignment", "cancel_assignment",
    "progress_update", "blocked_request", "submission", "resubmission",
    "teacher_feedback", "revision_request", "completion_decision",
    "parent_opt_in", "parent_digest_request", "escalation_ack",
    "admin_config_change", "roster_import", "policy_upload",
    "unknown", "unsafe", "out_of_scope",
]

# Role-based intent restrictions
ROLE_DENIED_INTENTS = {
    "student": {"create_assignment", "update_assignment", "cancel_assignment", 
                "teacher_feedback", "revision_request", "completion_decision",
                "admin_config_change", "roster_import", "policy_upload"},
    "guardian": {"create_assignment", "update_assignment", "cancel_assignment",
                "teacher_feedback", "revision_request", "completion_decision",
                "submission", "resubmission", "progress_update", "blocked_request",
                "admin_config_change", "roster_import", "policy_upload"},
}

client = None
def get_client():
    global client
    if client is None and settings.OPENAI_API_KEY:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return client

from app.agents.llm_factory import LLMFactory

async def classify_intent(message: str, user_role: str, context: dict = None) -> DetectedIntent:
    try:
        result = LLMFactory.parse_structured(
            prompt=f"User role: {user_role}\nMessage: {message}\nContext: {context or {}}",
            response_schema=DetectedIntent,
            system_prompt=INTENT_CLASSIFICATION_PROMPT
        )
        
        # Deterministic override: reject intents that don't match role permissions
        denied = ROLE_DENIED_INTENTS.get(user_role, set())
        if result.intent in denied:
            result.intent = "out_of_scope"
            result.is_safe = False
            result.reasoning = f"Role '{user_role}' cannot perform {result.intent}"
        
        # Validate intent is in our list
        if result.intent not in VALID_INTENTS:
            result.intent = "unknown"
            result.reasoning = f"Unrecognized intent mapped to unknown"
        
        return result
    except Exception as e:
        return DetectedIntent(
            intent="unknown",
            confidence=0.0,
            reasoning=f"Intent classification failed: {str(e)}",
            is_safe=True
        )
