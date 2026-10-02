import re

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"you\s+are\s+now\s+a",
    r"system\s*:\s*",
    r"<\|.*?\|>",
    r"\[INST\]",
    r"forget\s+(everything|all)",
    r"disregard\s+(all|previous)",
    r"new\s+instructions?",
]

def sanitize_document_text(text: str) -> str:
    flags = []
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            flags.append(f"Suspicious pattern detected matching: {pattern}")
    
    safe_text = f"<DOCUMENT_CONTENT>\n{text}\n</DOCUMENT_CONTENT>"
    
    if flags:
        safe_text += f"\n\n<SAFETY_FLAGS>\n" + "\n".join(flags) + "\n</SAFETY_FLAGS>"
    
    return safe_text

def check_for_injection(text: str) -> list[str]:
    flags = []
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            flags.append(f"Potential injection: {pattern}")
    return flags
