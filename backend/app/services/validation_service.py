from datetime import date
from decimal import Decimal
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.extraction import ExtractionResult
from app.models.fdr import FDRInstrument, FDRStatus
from app.models.validation import FindingSeverity, FindingType, ValidationFinding


async def cross_validate_fdr(
    fdr: FDRInstrument,
    extraction: ExtractionResult,
    db: AsyncSession,
) -> Tuple[List[ValidationFinding], int, List[str]]:
    extracted = extraction.extracted_fields or {}
    findings: List[ValidationFinding] = []
    priority_score = 0
    priority_reasons: List[str] = []

    # 1. Validate FDR Number
    ext_fdr_num = extracted.get("fdr_number")
    if ext_fdr_num:
        if str(ext_fdr_num).strip().lower() == str(fdr.fdr_number).strip().lower():
            findings.append(
                ValidationFinding(
                    fdr_instrument_id=fdr.id,
                    field_name="fdr_number",
                    submitted_value=fdr.fdr_number,
                    extracted_value=str(ext_fdr_num),
                    finding_type=FindingType.MATCH,
                    severity=FindingSeverity.INFO,
                    description="FDR instrument number matches extracted certificate.",
                )
            )
        else:
            findings.append(
                ValidationFinding(
                    fdr_instrument_id=fdr.id,
                    field_name="fdr_number",
                    submitted_value=fdr.fdr_number,
                    extracted_value=str(ext_fdr_num),
                    finding_type=FindingType.MISMATCH,
                    severity=FindingSeverity.CRITICAL,
                    description=f"Submitted FDR number '{fdr.fdr_number}' does not match extracted '{ext_fdr_num}'.",
                )
            )
            priority_score += 40
            priority_reasons.append("Instrument number mismatch between form and certificate")
    else:
        findings.append(
            ValidationFinding(
                fdr_instrument_id=fdr.id,
                field_name="fdr_number",
                submitted_value=fdr.fdr_number,
                extracted_value=None,
                finding_type=FindingType.MISSING_IN_DOCUMENT,
                severity=FindingSeverity.WARNING,
                description="FDR number could not be reliably extracted from uploaded receipt.",
            )
        )
        priority_score += 15
        priority_reasons.append("Instrument number unreadable or absent on document")

    # 2. Validate Deposit Amount
    ext_amt = extracted.get("deposit_amount")
    if ext_amt is not None:
        try:
            ext_amt_dec = Decimal(str(ext_amt))
            diff = abs(fdr.deposit_amount - ext_amt_dec)
            if diff == 0:
                findings.append(
                    ValidationFinding(
                        fdr_instrument_id=fdr.id,
                        field_name="deposit_amount",
                        submitted_value=str(fdr.deposit_amount),
                        extracted_value=str(ext_amt_dec),
                        finding_type=FindingType.MATCH,
                        severity=FindingSeverity.INFO,
                        description="Deposit amount perfectly matches extracted document value.",
                    )
                )
            else:
                findings.append(
                    ValidationFinding(
                        fdr_instrument_id=fdr.id,
                        field_name="deposit_amount",
                        submitted_value=str(fdr.deposit_amount),
                        extracted_value=str(ext_amt_dec),
                        finding_type=FindingType.MISMATCH,
                        severity=FindingSeverity.CRITICAL,
                        description=f"Amount discrepancy detected: Form specifies {fdr.deposit_amount} while receipt indicates {ext_amt_dec}.",
                    )
                )
                priority_score += 45
                priority_reasons.append(f"Deposit amount mismatch of {fdr.currency} {diff}")
        except Exception:
            pass

    # 3. Validate Bank Name
    ext_bank = extracted.get("bank_name")
    if ext_bank:
        if ext_bank.strip().lower() in fdr.bank_name.strip().lower() or fdr.bank_name.strip().lower() in ext_bank.strip().lower():
            findings.append(
                ValidationFinding(
                    fdr_instrument_id=fdr.id,
                    field_name="bank_name",
                    submitted_value=fdr.bank_name,
                    extracted_value=ext_bank,
                    finding_type=FindingType.MATCH,
                    severity=FindingSeverity.INFO,
                    description="Bank name verified successfully.",
                )
            )
        else:
            findings.append(
                ValidationFinding(
                    fdr_instrument_id=fdr.id,
                    field_name="bank_name",
                    submitted_value=fdr.bank_name,
                    extracted_value=ext_bank,
                    finding_type=FindingType.MISMATCH,
                    severity=FindingSeverity.WARNING,
                    description=f"Issuing bank difference: Submitted '{fdr.bank_name}', document says '{ext_bank}'.",
                )
            )
            priority_score += 20
            priority_reasons.append("Bank name mismatch")

    # 4. Check maturity date proximity
    days_to_maturity = (fdr.maturity_date - date.today()).days
    if days_to_maturity <= 30:
        priority_score += 25
        priority_reasons.append(f"Matures in {max(days_to_maturity, 0)} days")

    # Cap score at 100
    priority_score = min(priority_score, 100)

    # Persist findings
    db.add_all(findings)

    # Update instrument
    fdr.review_priority_score = priority_score
    fdr.review_priority_reasons = priority_reasons
    if any(f.severity == FindingSeverity.CRITICAL for f in findings):
        fdr.status = FDRStatus.CORRECTION_REQUESTED
    else:
        fdr.status = FDRStatus.VALIDATED

    await db.flush()
    return findings, priority_score, priority_reasons
