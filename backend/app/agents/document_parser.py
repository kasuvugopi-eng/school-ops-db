import pymupdf
import pdfplumber
import docx
import csv
import io
from openai import OpenAI
from app.config import settings
from app.agents.extraction_schemas import ParsedAssignment, ParsedRoster, ParsedPolicy
from app.agents.prompts import ASSIGNMENT_PARSE_PROMPT, ROSTER_PARSE_PROMPT
from app.agents.safety import sanitize_document_text

client = None
def get_openai_client():
    global client
    if client is None and settings.OPENAI_API_KEY:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return client

def extract_text_from_pdf(file_path: str) -> str:
    doc = pymupdf.open(file_path)
    text = "\n".join([page.get_text() for page in doc])
    doc.close()
    return text

def extract_text_from_docx(file_path: str) -> str:
    doc = docx.Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs if p.text])

def extract_text_from_csv(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def extract_text(file_path: str, mime_type: str) -> str:
    if 'pdf' in mime_type:
        return extract_text_from_pdf(file_path)
    elif 'docx' in mime_type or 'word' in mime_type:
        return extract_text_from_docx(file_path)
    elif 'csv' in mime_type or file_path.endswith('.csv'):
        return extract_text_from_csv(file_path)
    elif 'text' in mime_type:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        # Try as text
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

async def parse_assignment_document(text: str) -> ParsedAssignment:
    openai_client = get_openai_client()
    if not openai_client:
        # Fallback: return empty with ambiguity note
        return ParsedAssignment(
            ambiguities=["OpenAI API key not configured. Manual entry required."],
            confidence=0.0
        )
    
    safe_text = sanitize_document_text(text)
    completion = openai_client.beta.chat.completions.parse(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": ASSIGNMENT_PARSE_PROMPT},
            {"role": "user", "content": f"Extract assignment information:\n\n{safe_text}"}
        ],
        response_format=ParsedAssignment,
    )
    message = completion.choices[0].message
    if message.refusal:
        return ParsedAssignment(
            ambiguities=[f"Model refused to parse: {message.refusal}"],
            confidence=0.0
        )
    result = message.parsed
    # Auto-flag missing critical fields
    if not result.title:
        result.ambiguities.append("Title could not be determined")
    if not result.due_date:
        result.ambiguities.append("Due date not found or unclear")
    if not result.instructions:
        result.ambiguities.append("No clear instructions found")
    return result

async def parse_roster_document(text: str) -> ParsedRoster:
    openai_client = get_openai_client()
    if not openai_client:
        # Fallback: try CSV parsing directly
        return parse_csv_roster(text)
    
    safe_text = sanitize_document_text(text)
    completion = openai_client.beta.chat.completions.parse(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": ROSTER_PARSE_PROMPT},
            {"role": "user", "content": f"Extract roster information:\n\n{safe_text}"}
        ],
        response_format=ParsedRoster,
    )
    message = completion.choices[0].message
    if message.refusal:
        return ParsedRoster(rows=[], ambiguities=[f"Model refused: {message.refusal}"])
    return message.parsed

def parse_csv_roster(text: str) -> ParsedRoster:
    """Fallback CSV parser without LLM."""
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    seen_names = set()
    duplicates = []
    
    for i, row in enumerate(reader):
        # Try common column name variations
        name = row.get('student_name') or row.get('name') or row.get('Student Name') or row.get('Name') or ''
        grade = row.get('grade_class') or row.get('class') or row.get('Grade') or row.get('Class') or ''
        parent = row.get('parent_name') or row.get('Parent Name') or row.get('parent') or ''
        contact = row.get('parent_contact') or row.get('Parent Contact') or row.get('phone') or row.get('Phone') or ''
        notes = row.get('notes') or row.get('Notes') or ''
        
        flags = []
        if not name.strip():
            flags.append('Missing student name')
        if not grade.strip():
            flags.append('Missing class/grade')
        if name.strip().lower() in seen_names:
            flags.append('Possible duplicate')
            duplicates.append({'row': i, 'name': name.strip()})
        seen_names.add(name.strip().lower())
        
        from app.agents.extraction_schemas import ParsedRosterRow
        rows.append(ParsedRosterRow(
            student_name=name.strip(),
            grade_class=grade.strip() or None,
            parent_name=parent.strip() or None,
            parent_contact=contact.strip() or None,
            notes=notes.strip() or None,
            flags=flags
        ))
    
    return ParsedRoster(rows=rows, duplicate_candidates=duplicates)
