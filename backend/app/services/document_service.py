import uuid
import os
import shutil
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import Document
from app.models.enums import DocumentType

UPLOAD_DIR = "uploads"

async def upload_document(db: AsyncSession, file: UploadFile, school_id: uuid.UUID, uploaded_by: uuid.UUID, document_type: DocumentType, owner_type: str = None, owner_id: uuid.UUID = None):
    school_dir = os.path.join(UPLOAD_DIR, str(school_id))
    os.makedirs(school_dir, exist_ok=True)
    
    filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(school_dir, filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    doc = Document(
        school_id=school_id,
        uploaded_by=uploaded_by,
        document_type=document_type,
        original_filename=file.filename,
        file_path=file_path,
        mime_type=file.content_type,
        owner_type=owner_type,
        owner_id=owner_id
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc

async def get_document(db: AsyncSession, document_id: uuid.UUID):
    result = await db.execute(select(Document).where(Document.id == document_id))
    return result.scalar_one_or_none()

async def list_documents(db: AsyncSession, school_id: uuid.UUID, document_type: DocumentType = None):
    query = select(Document).where(Document.school_id == school_id)
    if document_type:
        query = query.where(Document.document_type == document_type)
    result = await db.execute(query)
    return result.scalars().all()

def get_document_file_path(document: Document) -> str:
    return os.path.abspath(document.file_path)
