import hashlib
import os
import uuid
from typing import Tuple
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.core.exceptions import ValidationException
from app.models.document import DocumentUploadType, FDRDocument


async def save_uploaded_document(
    fdr_instrument_id: uuid.UUID,
    file: UploadFile,
    upload_type: DocumentUploadType,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Tuple[FDRDocument, bytes]:
    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Read content and compute hash
    content = await file.read()
    file_size = len(content)

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise ValidationException(f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB}MB")

    file_hash = hashlib.sha256(content).hexdigest()

    # Generate safe unique filename
    ext = os.path.splitext(file.filename or "receipt.pdf")[1].lower()
    stored_filename = f"{fdr_instrument_id}_{uuid.uuid4().hex[:10]}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, stored_filename)

    # Save to disk
    with open(file_path, "wb") as f:
        f.write(content)

    doc = FDRDocument(
        fdr_instrument_id=fdr_instrument_id,
        original_filename=file.filename or "uploaded_document",
        stored_filename=stored_filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        file_hash_sha256=file_hash,
        upload_type=upload_type,
        uploaded_by=user_id,
    )
    db.add(doc)
    await db.flush()

    return doc, content
