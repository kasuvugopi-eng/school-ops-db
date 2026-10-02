# ADR-002: LLM Output as Proposed Action

## Status
**Accepted** — October 2026

## Context
The system uses GPT-4o to parse documents (assignment briefs, rosters, policies) and classify chat message intents. LLMs can hallucinate, misinterpret ambiguous text, or be manipulated via prompt injection embedded in uploaded documents.

In a school context, incorrect data can have real consequences:
- A wrong due date could cause students to miss deadlines.
- A misidentified student could receive the wrong assignment.
- An injected prompt in a PDF could cause unintended system actions.

## Decision
**LLM output is always treated as a "proposed action" — never written directly to the database without validation and, for high-impact actions, human approval.**

### Implementation
1. **Document parsing** produces a `DocumentParseResult` with `approval_state=PENDING`. The extracted data is stored alongside confidence scores and ambiguity flags. A teacher/admin must review and approve before the system creates assignments or imports roster data.

2. **Intent classification** output is validated against deterministic business rules:
   - Role-based restrictions override LLM classification (e.g., if the LLM classifies a student message as `create_assignment`, the system overrides to `out_of_scope`).
   - Invalid intents are mapped to `unknown`.
   - Unsafe content is flagged and blocked.

3. **Prompt injection defense**:
   - Document text is wrapped in `<DOCUMENT_CONTENT>` tags to separate data from instructions.
   - Suspicious patterns (e.g., "ignore previous instructions") are flagged in `<SAFETY_FLAGS>`.
   - Flagged documents still get parsed, but the flags are shown to the reviewer.

## Consequences
### Positive
- No silent data corruption from LLM errors.
- Teachers maintain control over what enters the system.
- Audit trail captures both the raw LLM output and the human decision.
- Prompt injection in documents is detected and surfaced, not silently executed.

### Negative
- Slightly slower workflow (teacher must approve parsed documents).
- Additional UI complexity for the parse review flow.
- If the LLM is unavailable, document parsing falls back to manual entry only.
