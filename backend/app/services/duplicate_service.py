from typing import List, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.document import FDRDocument
from app.models.duplicate import DuplicateCandidate, DuplicateStatus
from app.models.fdr import FDRInstrument


async def check_and_flag_duplicates(
    fdr: FDRInstrument,
    document: Optional[FDRDocument],
    db: AsyncSession,
) -> List[DuplicateCandidate]:
    candidates: List[DuplicateCandidate] = []

    # 1. Find records sharing this file's hash.
    hash_matching_fdr_ids = set()
    if document and document.file_hash_sha256:
        hash_stmt = select(FDRDocument).where(
            FDRDocument.id != document.id,
            FDRDocument.fdr_instrument_id != fdr.id,
            FDRDocument.file_hash_sha256 == document.file_hash_sha256,
        )
        hash_docs = (await db.execute(hash_stmt)).scalars().all()
        for hd in hash_docs:
            hash_matching_fdr_ids.add(hd.fdr_instrument_id)

    # 2. Include hash-only matches, even when the receipt metadata differs.
    stmt = (
        select(FDRInstrument)
        .options(selectinload(FDRInstrument.institution))
        .where(
            FDRInstrument.id != fdr.id,
            or_(
                FDRInstrument.fdr_number.ilike(fdr.fdr_number.strip()),
                (
                    (FDRInstrument.bank_name.ilike(fdr.bank_name.strip()))
                    & (FDRInstrument.deposit_amount == fdr.deposit_amount)
                    & (FDRInstrument.maturity_date == fdr.maturity_date)
                ),
                FDRInstrument.id.in_(hash_matching_fdr_ids),
            ),
        )
    )
    result = await db.execute(stmt)
    matching_instruments = result.scalars().all()

    for other in matching_instruments:
        match_score = 0.0
        reasons = []
        matching_fields = {}
        differing_fields = {}

        # FDR Number comparison
        if other.fdr_number.strip().lower() == fdr.fdr_number.strip().lower():
            match_score += 0.60
            reasons.append(f"Identical FDR Number '{fdr.fdr_number}'")
            matching_fields["fdr_number"] = fdr.fdr_number
        else:
            differing_fields["fdr_number"] = f"{fdr.fdr_number} vs {other.fdr_number}"

        # Bank and amount comparison
        if other.bank_name.strip().lower() == fdr.bank_name.strip().lower():
            match_score += 0.20
            matching_fields["bank_name"] = fdr.bank_name
        else:
            differing_fields["bank_name"] = f"{fdr.bank_name} vs {other.bank_name}"

        if other.deposit_amount == fdr.deposit_amount:
            match_score += 0.15
            matching_fields["deposit_amount"] = str(fdr.deposit_amount)
        else:
            differing_fields["deposit_amount"] = f"{fdr.deposit_amount} vs {other.deposit_amount}"

        file_hash_match = other.id in hash_matching_fdr_ids
        if file_hash_match:
            match_score = 0.99
            reasons.append("Identical PDF document cryptographic hash match")

        match_score = min(match_score, 0.99)

        if match_score >= 0.70:
            candidate = DuplicateCandidate(
                fdr_instrument_a_id=fdr.id,
                fdr_instrument_b_id=other.id,
                match_score=round(match_score, 2),
                match_reasons=reasons,
                matching_fields=matching_fields,
                differing_fields=differing_fields,
                file_hash_match=file_hash_match,
                status=DuplicateStatus.PENDING,
                review_notes="Automated duplicate candidate identified during validation.",
            )
            candidates.append(candidate)
            db.add(candidate)

    if candidates:
        fdr.has_potential_duplicate = True
        fdr.review_priority_score = min(fdr.review_priority_score + 35, 100)
        reasons_list = fdr.review_priority_reasons or []
        if "Potential duplicate candidate flagged" not in reasons_list:
            reasons_list.append("Potential duplicate candidate flagged")
            fdr.review_priority_reasons = reasons_list

    await db.flush()
    return candidates
