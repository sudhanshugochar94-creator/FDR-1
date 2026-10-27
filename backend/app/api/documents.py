import os
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import ensure_fdr_institution_access, get_current_user
from app.core.exceptions import NotFoundException
from app.database import get_db
from app.models.audit import AuditEvent
from app.models.document import DocumentUploadType, FDRDocument
from app.models.extraction import ExtractionResult
from app.models.fdr import FDRInstrument
from app.models.user import User
from app.schemas.fdr import DocumentBrief, ExtractionBrief
from app.services.document_service import save_uploaded_document
from app.services.agent_service import run_fdr_agent_workflow
from app.services.duplicate_service import check_and_flag_duplicates
from app.services.extraction_service import process_document_extraction
from app.services.validation_service import cross_validate_fdr

router = APIRouter(tags=["Documents & Extraction"])


@router.post("/fdrs/{fdr_id}/documents", response_model=DocumentBrief, status_code=status.HTTP_201_CREATED)
async def upload_fdr_document(
    fdr_id: UUID,
    file: UploadFile = File(...),
    upload_type: DocumentUploadType = Form(DocumentUploadType.ORIGINAL),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentBrief:
    # 1. Fetch FDR
    stmt = select(FDRInstrument).where(FDRInstrument.id == fdr_id)
    fdr = (await db.execute(stmt)).scalars().first()
    if not fdr:
        raise NotFoundException(f"FDR instrument {fdr_id} not found")

    # Scoping check
    await ensure_fdr_institution_access(fdr=fdr, user=current_user, db=db)

    # 2. Save document to disk & DB
    doc, file_bytes = await save_uploaded_document(
        fdr_instrument_id=fdr.id,
        file=file,
        upload_type=upload_type,
        user_id=current_user.id,
        db=db,
    )

    # 3. Process automated text extraction
    extraction = await process_document_extraction(
        document=doc,
        file_bytes=file_bytes,
        db=db,
    )

    # 4. Cross-validate submitted data vs extracted data
    await cross_validate_fdr(fdr=fdr, extraction=extraction, db=db)

    # 5. Check for cross-institutional duplicates
    await check_and_flag_duplicates(fdr=fdr, document=doc, db=db)

    # 6. Audit log
    audit = AuditEvent(
        user_id=current_user.id,
        role=current_user.role.value,
        action="DOCUMENT_UPLOADED",
        entity_type="FDRDocument",
        entity_id=doc.id,
        after_values={
            "original_filename": doc.original_filename,
            "sha256": doc.file_hash_sha256,
            "file_size": doc.file_size,
        },
        reason="FDR certificate uploaded and processed",
    )
    db.add(audit)
    await run_fdr_agent_workflow(
        fdr=fdr,
        user=current_user,
        db=db,
        generate_ai_summary=False,
    )
    await db.commit()
    await db.refresh(doc)

    return DocumentBrief.model_validate(doc)


@router.get("/fdrs/{fdr_id}/documents", response_model=List[DocumentBrief])
async def list_fdr_documents(
    fdr_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[DocumentBrief]:
    fdr_stmt = select(FDRInstrument).where(FDRInstrument.id == fdr_id)
    fdr = (await db.execute(fdr_stmt)).scalars().first()
    if not fdr:
        raise NotFoundException(f"FDR instrument {fdr_id} not found")
    await ensure_fdr_institution_access(fdr=fdr, user=current_user, db=db)

    stmt = select(FDRDocument).where(FDRDocument.fdr_instrument_id == fdr_id).order_by(FDRDocument.created_at.desc())
    docs = (await db.execute(stmt)).scalars().all()
    return [DocumentBrief.model_validate(d) for d in docs]


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(FDRDocument).where(FDRDocument.id == document_id)
    doc = (await db.execute(stmt)).scalars().first()
    if not doc:
        raise NotFoundException(f"Document file not found on server")

    fdr_stmt = select(FDRInstrument).where(FDRInstrument.id == doc.fdr_instrument_id)
    fdr = (await db.execute(fdr_stmt)).scalars().first()
    if not fdr:
        raise NotFoundException(f"FDR instrument for document {document_id} not found")
    await ensure_fdr_institution_access(fdr=fdr, user=current_user, db=db)
    if not os.path.exists(doc.file_path):
        raise NotFoundException(f"Document file not found on server")

    return FileResponse(
        path=doc.file_path,
        filename=doc.original_filename,
        media_type=doc.mime_type,
    )


@router.get("/documents/{document_id}/extractions", response_model=List[ExtractionBrief])
async def get_document_extractions(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ExtractionBrief]:
    document_stmt = select(FDRDocument).where(FDRDocument.id == document_id)
    document = (await db.execute(document_stmt)).scalars().first()
    if not document:
        raise NotFoundException(f"Document {document_id} not found")

    fdr_stmt = select(FDRInstrument).where(FDRInstrument.id == document.fdr_instrument_id)
    fdr = (await db.execute(fdr_stmt)).scalars().first()
    if not fdr:
        raise NotFoundException(f"FDR instrument for document {document_id} not found")
    await ensure_fdr_institution_access(fdr=fdr, user=current_user, db=db)

    stmt = select(ExtractionResult).where(ExtractionResult.document_id == document_id).order_by(ExtractionResult.created_at.desc())
    results = (await db.execute(stmt)).scalars().all()
    return [ExtractionBrief.model_validate(r) for r in results]
