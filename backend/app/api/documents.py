import uuid
import os
import aiofiles
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.auth.permissions import assert_same_school
from app.models.enums import UserRole, DocumentType, ParseApprovalState, AssignmentState, AssignmentTargetType
from app.models.user import User
from app.models.document import Document
from app.models.document_parse import DocumentParseResult
from app.models.assignment import Assignment
from app.agents.document_parser import extract_text, parse_assignment_document, parse_roster_document
from app.services.audit_service import log_event
from app.websocket.events import emit_parse_ready
from app.config import settings

router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid document_type: {document_type}")
    
    # Create directory
    school_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.school_id))
    os.makedirs(school_dir, exist_ok=True)
    
    # Save file
    file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
    saved_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(school_dir, saved_filename)
    
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large. Max {settings.MAX_UPLOAD_SIZE_MB}MB")
    
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    doc = Document(
        school_id=current_user.school_id,
        uploaded_by=current_user.id,
        document_type=doc_type,
        original_filename=file.filename or "unknown",
        file_path=file_path,
        mime_type=file.content_type,
        file_size=len(content)
    )
    db.add(doc)
    await log_event(db, "document.uploaded", school_id=current_user.school_id,
                    actor_id=current_user.id, resource_type="document",
                    resource_id=doc.id, details={"filename": file.filename, "type": document_type})
    await db.commit()
    await db.refresh(doc)
    
    return {
        "id": str(doc.id), "document_type": doc.document_type.value,
        "original_filename": doc.original_filename, "mime_type": doc.mime_type,
        "file_size": doc.file_size, "created_at": str(doc.created_at)
    }

@router.get("")
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Document).where(Document.school_id == current_user.school_id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    
    docs_out = []
    for d in docs:
        pr_result = await db.execute(
            select(DocumentParseResult)
            .where(DocumentParseResult.document_id == d.id)
            .order_by(DocumentParseResult.created_at.desc())
            .limit(1)
        )
        pr = pr_result.scalar_one_or_none()
        
        doc_dict = {
            "id": str(d.id), "document_type": d.document_type.value,
            "original_filename": d.original_filename, "mime_type": d.mime_type,
            "file_size": d.file_size, "uploaded_by": str(d.uploaded_by),
            "created_at": str(d.created_at)
        }
        if pr:
            doc_dict["approval_state"] = pr.approval_state.value
            doc_dict["parse_result_id"] = str(pr.id)
            
        docs_out.append(doc_dict)
        
    return docs_out

@router.get("/{id}")
async def get_document(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Document).where(Document.id == id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    assert_same_school(current_user, doc.school_id)
    return {
        "id": str(doc.id), "document_type": doc.document_type.value,
        "original_filename": doc.original_filename, "mime_type": doc.mime_type,
        "file_size": doc.file_size, "uploaded_by": str(doc.uploaded_by),
        "created_at": str(doc.created_at)
    }

@router.post("/{id}/parse")
async def parse_document(
    id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Document).where(Document.id == id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    assert_same_school(current_user, doc.school_id)
    
    # Validate document type before text extraction
    if doc.document_type not in (DocumentType.ASSIGNMENT_BRIEF, DocumentType.ROSTER):
        raise HTTPException(status_code=400, detail="Parsing not supported for this document type")
        
    # Extract text from document
    try:
        text = extract_text(doc.file_path, doc.mime_type or "text/plain")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract text: {str(e)}")
    
    # Parse based on document type
    try:
        if doc.document_type == DocumentType.ASSIGNMENT_BRIEF:
            parsed = await parse_assignment_document(text)
        elif doc.document_type == DocumentType.ROSTER:
            parsed = await parse_roster_document(text)
    except HTTPException:
        raise
    except Exception as e:
        await log_event(db, "document.parse_failed", school_id=doc.school_id,
                        actor_id=current_user.id, resource_type="document",
                        resource_id=doc.id, details={"error": str(e)})
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")
    
    ambiguity_flags = getattr(parsed, 'ambiguities', [])
    approval_state = ParseApprovalState.PENDING
    clarification_question = None
    
    if doc.document_type == DocumentType.ASSIGNMENT_BRIEF and ambiguity_flags:
        approval_state = ParseApprovalState.NEEDS_CLARIFICATION
        clarification_question = f"Please clarify: {'; '.join(ambiguity_flags)}"
    
    # Check if a parse result already exists
    pr_result = await db.execute(
        select(DocumentParseResult).where(DocumentParseResult.document_id == doc.id)
    )
    parse_result = pr_result.scalar_one_or_none()
    
    is_new = False
    if not parse_result:
        parse_result = DocumentParseResult(document_id=doc.id)
        db.add(parse_result)
        is_new = True
        
    parse_result.parsed_data = parsed.model_dump()
    parse_result.confidence_notes = {"overall_confidence": getattr(parsed, 'confidence', 0.0)}
    parse_result.ambiguity_flags = ambiguity_flags
    parse_result.approval_state = approval_state
    parse_result.clarification_question = clarification_question
    parse_result.model_used = settings.OPENAI_MODEL
    parse_result.raw_model_response = str(parsed.model_dump())
    
    if is_new:
        await log_event(db, "document.parsed", school_id=doc.school_id,
                        actor_id=current_user.id, resource_type="document_parse",
                        resource_id=parse_result.id, details={"ambiguities": parse_result.ambiguity_flags})
    else:
        await log_event(db, "document.reparsed", school_id=doc.school_id,
                        actor_id=current_user.id, resource_type="document_parse",
                        resource_id=parse_result.id, details={"ambiguities": parse_result.ambiguity_flags})
                        
    if approval_state == ParseApprovalState.NEEDS_CLARIFICATION:
        await log_event(db, "document.clarification_requested", school_id=doc.school_id,
                        actor_id=current_user.id, resource_type="document_parse",
                        resource_id=parse_result.id, details={"question": clarification_question})
    await db.commit()
    await db.refresh(parse_result)
    
    await emit_parse_ready(str(doc.school_id), {
        "document_id": str(doc.id), "parse_result_id": str(parse_result.id),
        "filename": doc.original_filename
    })
    
    return {
        "id": str(parse_result.id), "document_id": str(doc.id),
        "parsed_data": parse_result.parsed_data,
        "ambiguity_flags": parse_result.ambiguity_flags,
        "confidence_notes": parse_result.confidence_notes,
        "approval_state": parse_result.approval_state.value,
        "created_at": str(parse_result.created_at)
    }

@router.get("/{id}/parse-result")
async def get_parse_result(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    doc_result = await db.execute(select(Document).where(Document.id == id))
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    assert_same_school(current_user, doc.school_id)
    
    result = await db.execute(
        select(DocumentParseResult).where(DocumentParseResult.document_id == id)
        .order_by(DocumentParseResult.created_at.desc())
    )
    parse_result = result.scalar_one_or_none()
    if not parse_result:
        raise HTTPException(status_code=404, detail="No parse result found")
    
    return {
        "id": str(parse_result.id), "document_id": str(id),
        "parsed_data": parse_result.parsed_data,
        "ambiguity_flags": parse_result.ambiguity_flags,
        "confidence_notes": parse_result.confidence_notes,
        "approval_state": parse_result.approval_state.value,
        "created_at": str(parse_result.created_at)
    }

@router.post("/{id}/approve")
async def approve_parse(
    id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db)
):
    doc_result = await db.execute(select(Document).where(Document.id == id))
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    assert_same_school(current_user, doc.school_id)
    
    result = await db.execute(
        select(DocumentParseResult).where(
            DocumentParseResult.document_id == id
        ).order_by(DocumentParseResult.created_at.desc())
    )
    parse_result = result.scalar_one_or_none()
    if not parse_result:
        raise HTTPException(status_code=404, detail="No parse result found")
    if parse_result.approval_state == ParseApprovalState.NEEDS_CLARIFICATION:
        raise HTTPException(status_code=409, detail="Document requires clarification before approval")
    if parse_result.approval_state != ParseApprovalState.PENDING:
        raise HTTPException(status_code=404, detail="No pending parse result")
    
    parse_result.approval_state = ParseApprovalState.APPROVED
    parse_result.approved_by = current_user.id
    parse_result.approved_at = datetime.now(timezone.utc)
    
    # If assignment brief, create assignment from parsed data
    created_assignment = None
    if doc.document_type == DocumentType.ASSIGNMENT_BRIEF:
        parsed = parse_result.parsed_data
        
        due_date_str = parsed.get("due_date")
        due_date_dt = None
        if due_date_str:
            try:
                due_date_dt = datetime.strptime(due_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
                
        assignment = Assignment(
            school_id=doc.school_id,
            created_by=current_user.id,
            title=parsed.get("title", "Untitled Assignment"),
            subject=parsed.get("subject"),
            instructions=parsed.get("instructions"),
            due_date=due_date_dt,
            target_type=AssignmentTargetType.CLASS,
            state=AssignmentState.DRAFT,
            source_document_id=doc.id
        )
        db.add(assignment)
        await db.flush()
        created_assignment = assignment
    
    await log_event(db, "document.approved", school_id=doc.school_id,
                    actor_id=current_user.id, resource_type="document_parse",
                    resource_id=parse_result.id)
    await db.commit()
    
    response = {"approval_state": "APPROVED", "parse_result_id": str(parse_result.id)}
    if created_assignment:
        response["created_assignment_id"] = str(created_assignment.id)
        response["created_assignment_title"] = created_assignment.title
    return response

from pydantic import BaseModel

class ClarifyRequest(BaseModel):
    response: str

@router.post("/{id}/clarify")
async def clarify_parse(
    id: uuid.UUID,
    req: ClarifyRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.TEACHER)),
    db: AsyncSession = Depends(get_db)
):
    doc_result = await db.execute(select(Document).where(Document.id == id))
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    assert_same_school(current_user, doc.school_id)
    
    result = await db.execute(
        select(DocumentParseResult).where(
            DocumentParseResult.document_id == id
        ).order_by(DocumentParseResult.created_at.desc())
    )
    parse_result = result.scalar_one_or_none()
    if not parse_result or parse_result.approval_state != ParseApprovalState.NEEDS_CLARIFICATION:
        raise HTTPException(status_code=400, detail="Document does not need clarification")
    
    parse_result.clarification_response = req.response
    
    try:
        text = extract_text(doc.file_path, doc.mime_type or "text/plain")
        text += f"\n\n[Clarification provided by user]: {req.response}"
        
        if doc.document_type == DocumentType.ASSIGNMENT_BRIEF:
            parsed = await parse_assignment_document(text)
        elif doc.document_type == DocumentType.ROSTER:
            parsed = await parse_roster_document(text)
            
        parse_result.parsed_data = parsed.model_dump()
        ambiguity_flags = getattr(parsed, "ambiguities", [])
        
        if doc.document_type == DocumentType.ASSIGNMENT_BRIEF and ambiguity_flags:
            parse_result.ambiguity_flags = ambiguity_flags
            parse_result.clarification_question = f"Please clarify: {'; '.join(ambiguity_flags)}"
            parse_result.approval_state = ParseApprovalState.NEEDS_CLARIFICATION
        else:
            parse_result.ambiguity_flags = []
            parse_result.approval_state = ParseApprovalState.PENDING
            parse_result.clarification_question = None
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reparsing failed: {str(e)}")
        
    await db.commit()
    await db.refresh(parse_result)
    
    return {
        "id": str(parse_result.id), "document_id": str(doc.id),
        "parsed_data": parse_result.parsed_data,
        "ambiguity_flags": parse_result.ambiguity_flags,
        "approval_state": parse_result.approval_state.value
    }
