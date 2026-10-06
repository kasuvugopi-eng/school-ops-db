"""Helpers to route Telegram teacher replies to the exact student/parent who sent the message.

Every message forwarded to a teacher carries a reference tag ("Ref: #<user-uuid>").
When the teacher uses Telegram's Reply on that message, we read the tag from the
original message and deliver the answer only to that user.
"""
import re
import uuid
from typing import Optional

_REF_RE = re.compile(r"Ref:\s*#([0-9a-fA-F-]{36})")


def ref_tag(user_id) -> str:
    return f"\n\n🔖 Ref: #{user_id}\n↩️ Reply to this message to answer."


def extract_ref(text: Optional[str]) -> Optional[uuid.UUID]:
    if not text:
        return None
    m = _REF_RE.search(text)
    if not m:
        return None
    try:
        return uuid.UUID(m.group(1))
    except ValueError:
        return None
