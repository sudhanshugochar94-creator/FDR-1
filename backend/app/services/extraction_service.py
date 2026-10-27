import io
import os
import re
import shutil
import time
from typing import Any, Dict, Optional, Tuple
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.core.exceptions import ValidationException
from app.models.document import FDRDocument
from app.models.extraction import ExtractionMethod, ExtractionResult


def extract_text_from_pdf(content: bytes) -> Tuple[str, Optional[str], bool]:
    """Extract PDF text, using Tesseract for scanned pages when available."""
    try:
        import pymupdf
    except ImportError:
        pymupdf = None

    if pymupdf is not None:
        try:
            doc = pymupdf.open(stream=content, filetype="pdf")
        except pymupdf.FileDataError as exc:
            raise ValidationException("The uploaded PDF could not be read.") from exc

        text = "\n".join(page.get_text() for page in doc).strip()
        if text:
            return text, None, False

        return _ocr_pdf_pages(doc)

    try:
        import pypdf
    except ImportError:
        return "", "pdf-text-extractor-unavailable", False

    text = ""
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    except (pypdf.errors.PdfReadError, ValueError, OSError) as exc:
        raise ValidationException("The uploaded PDF could not be read.") from exc

    if text.strip():
        return text.strip(), None, False
    return "", "pdf-rasterizer-unavailable", False


def _configure_tesseract(pytesseract: Any) -> None:
    if shutil.which("tesseract"):
        return

    install_roots = (
        os.environ.get("ProgramFiles", r"C:\Program Files"),
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
    )
    for root in install_roots:
        executable = os.path.join(root, "Tesseract-OCR", "tesseract.exe")
        if os.path.isfile(executable):
            pytesseract.pytesseract.tesseract_cmd = executable
            return


def _ocr_pdf_pages(pdf_document: Any) -> Tuple[str, Optional[str], bool]:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return "", "ocr-dependency-unavailable", True

    _configure_tesseract(pytesseract)
    extracted_pages = []
    try:
        for page in pdf_document:
            pixmap = page.get_pixmap(dpi=144, alpha=False)
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            extracted_pages.append(pytesseract.image_to_string(image))
    except pytesseract.TesseractNotFoundError:
        return "", "tesseract-unavailable", True
    except pytesseract.TesseractError as exc:
        raise ValidationException("Tesseract OCR could not process this document.") from exc

    return "\n".join(extracted_pages).strip(), None, True


def extract_text_from_image(content: bytes) -> Tuple[str, Optional[str]]:
    try:
        import pytesseract
        from PIL import Image, UnidentifiedImageError
    except ImportError:
        return "", "ocr-dependency-unavailable"

    _configure_tesseract(pytesseract)
    try:
        image = Image.open(io.BytesIO(content))
        return pytesseract.image_to_string(image).strip(), None
    except UnidentifiedImageError as exc:
        raise ValidationException("The uploaded image could not be read.") from exc
    except pytesseract.TesseractNotFoundError:
        return "", "tesseract-unavailable"
    except pytesseract.TesseractError as exc:
        raise ValidationException("Tesseract OCR could not process this document.") from exc


def extract_text_from_document(content: bytes, mime_type: str) -> Tuple[str, Optional[str], bool]:
    if mime_type == "application/pdf":
        return extract_text_from_pdf(content)
    if mime_type in {"image/jpeg", "image/jpg", "image/png"}:
        text, notice = extract_text_from_image(content)
        return text, notice, True
    raise ValidationException("Only PDF, JPG, and PNG documents can be processed.")


def parse_fdr_fields_heuristically(raw_text: str) -> Dict[str, Any]:
    """Pattern matching heuristics to extract FDR fields from raw text."""
    fields: Dict[str, Any] = {}
    confidence: Dict[str, float] = {}

    # 1. FDR / Account Number
    fdr_patterns = [
        r"(?:FDR|FD|Deposit|Receipt|Account|Certificate)\s*(?:No|Number|#)?[:.\s-]*([A-Z0-9-]{6,25})",
        r"(?:FDR|FD)[- ]*([A-Z0-9-]{6,25})",
    ]
    for pattern in fdr_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if not candidate.isalpha():
                fields["fdr_number"] = candidate
                confidence["fdr_number"] = 0.92
                break

    # 2. Deposit Amount
    amount_patterns = [
        r"(?:Rs\.?|INR|Amount|Principal|Deposit Amount)[:.\s]*([\d,]+(?:\.\d{2})?)",
        r"(?:₹)\s*([\d,]+(?:\.\d{2})?)",
        r"([\d,]+(?:\.\d{2})?)\s*(?:Only|\/-)",
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            raw_amt = match.group(1).replace(",", "").strip()
            try:
                amt_val = float(raw_amt)
                if amt_val > 1000:  # Reasonable deposit filter
                    fields["deposit_amount"] = amt_val
                    confidence["deposit_amount"] = 0.90
                    break
            except ValueError:
                continue

    # 3. Bank Name
    known_banks = [
        "State Bank of India",
        "HDFC Bank",
        "ICICI Bank",
        "Punjab National Bank",
        "Bank of Baroda",
        "Axis Bank",
        "Canara Bank",
        "Union Bank of India",
        "Kotak Mahindra Bank",
        "IndusInd Bank",
    ]
    for bank in known_banks:
        if bank.lower() in raw_text.lower():
            fields["bank_name"] = bank
            confidence["bank_name"] = 0.95
            break

    # 4. Dates
    date_patterns = [
        r"(?:Maturity|Expiry|Due Date)[:.\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(?:Issue|Deposit Date)[:.\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    ]
    mat_match = re.search(r"(?:Maturity|Expiry|Due Date)[:.\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", raw_text, re.IGNORECASE)
    if mat_match:
        fields["maturity_date"] = mat_match.group(1).strip()
        confidence["maturity_date"] = 0.88

    issue_match = re.search(r"(?:Issue|Deposit Date|Date of Issue)[:.\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", raw_text, re.IGNORECASE)
    if issue_match:
        fields["issue_date"] = issue_match.group(1).strip()
        confidence["issue_date"] = 0.88

    return {"extracted_fields": fields, "confidence_scores": confidence}


async def try_ollama_extraction(raw_text: str) -> Optional[Dict[str, Any]]:
    """Attempt extraction via local Ollama LLM if reachable."""
    if not settings.OLLAMA_BASE_URL:
        return None

    prompt = f"""
    Extract the following Fixed Deposit Receipt (FDR) fields from this text in JSON format:
    fdr_number, bank_name, deposit_amount, issue_date (YYYY-MM-DD), maturity_date (YYYY-MM-DD), branch_name.
    
    Text:
    {raw_text[:2000]}
    
    Return ONLY pure JSON.
    """
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "keep_alive": "10m",
                    "options": {
                        "temperature": 0,
                        "num_ctx": 2048,
                        "num_predict": 128,
                    },
                },
            )
            if resp.status_code == 200:
                import json
                res_data = resp.json()
                return json.loads(res_data.get("response", "{}"))
    except Exception:
        # Graceful fallback to heuristic extraction
        return None

    return None


async def process_document_extraction(
    document: FDRDocument,
    file_bytes: bytes,
    db: AsyncSession,
) -> ExtractionResult:
    start_time = time.time()

    # 1. Extract text without substituting placeholder text for an unreadable scan.
    raw_text, extraction_notice, used_ocr = extract_text_from_document(
        file_bytes,
        document.mime_type,
    )
    extraction_method = ExtractionMethod.OCR if used_ocr else ExtractionMethod.TEXT_EXTRACTION

    # 2. Parse fields
    heuristic_data = parse_fdr_fields_heuristically(raw_text)
    extracted_fields = heuristic_data["extracted_fields"]
    confidence_scores = heuristic_data["confidence_scores"]
    ai_model = extraction_notice or "heuristic-regex"

    required_fields = ("fdr_number", "deposit_amount", "bank_name", "maturity_date")
    has_required_fields = all(extracted_fields.get(field) for field in required_fields)

    # Ollama is only needed when local text extraction missed a core receipt field.
    if len(raw_text) > 50 and not has_required_fields:
        llm_fields = await try_ollama_extraction(raw_text)
        if llm_fields:
            extracted_fields.update({k: v for k, v in llm_fields.items() if v})
            ai_model = f"ollama-{settings.OLLAMA_MODEL}"
            extraction_method = ExtractionMethod.AI_ASSISTED

    elapsed_ms = int((time.time() - start_time) * 1000)

    result = ExtractionResult(
        document_id=document.id,
        extraction_method=extraction_method,
        raw_text=raw_text,
        extracted_fields=extracted_fields,
        confidence_scores=confidence_scores,
        ai_model_used=ai_model,
        processing_time_ms=elapsed_ms,
    )
    db.add(result)
    await db.flush()

    return result
