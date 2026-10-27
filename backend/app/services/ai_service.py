"""AI Service module for Ollama integration.

Provides health checks, model availability verification, structured extraction,
discrepancy explanation, case summaries, and natural-language query handling.
All AI features gracefully degrade when Ollama is unavailable.
"""

import json
import logging
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.audit import AuditEvent
from app.models.duplicate import DuplicateCandidate
from app.models.fdr import FDRInstrument, FDRStatus, VerificationStatus
from app.models.notification import Notification
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


# ─── Schemas ────────────────────────────────────────────────────────────────

class AIHealthResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    ollama_reachable: bool
    model_available: bool
    model_name: str
    base_url: str
    message: str


class DiscrepancyExplanation(BaseModel):
    summary: str
    conflicting_fields: List[Dict[str, Any]]
    why_it_matters: str
    evidence_to_inspect: List[str]
    recommended_action: str


class CaseSummary(BaseModel):
    fdr_reference: str
    current_status: str
    verification_status: str
    important_dates: Dict[str, str]
    unresolved_issues: List[str]
    previous_actions: List[str]
    pending_next_step: str
    ai_narrative: Optional[str] = None


class AssistantResponse(BaseModel):
    answer: str
    source_records: List[Dict[str, Any]] = []
    query_type: str
    ai_generated: bool = False


# ─── Ollama Client ──────────────────────────────────────────────────────────

async def check_ollama_health() -> AIHealthResponse:
    """Check if Ollama is reachable and the configured model is available."""
    base_url = settings.OLLAMA_BASE_URL
    model = settings.OLLAMA_MODEL

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check Ollama server
            resp = await client.get(f"{base_url}/api/tags")
            if resp.status_code != 200:
                return AIHealthResponse(
                    ollama_reachable=False, model_available=False,
                    model_name=model, base_url=base_url,
                    message=f"Ollama returned status {resp.status_code}"
                )

            # Check model availability
            models = resp.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            available = any(model in name for name in model_names)

            return AIHealthResponse(
                ollama_reachable=True, model_available=available,
                model_name=model, base_url=base_url,
                message="Ollama is healthy" + (
                    f" and model '{model}' is available" if available
                    else f". Model '{model}' not found. Available: {model_names}. Run: ollama pull {model}"
                )
            )
    except Exception as e:
        return AIHealthResponse(
            ollama_reachable=False, model_available=False,
            model_name=model, base_url=base_url,
            message=f"Cannot reach Ollama at {base_url}: {str(e)}"
        )


async def _call_ollama(
    prompt: str,
    system: str = "",
    timeout: float = 20.0,
    num_predict: int = 64,
) -> Optional[str]:
    """Make a request to the Ollama API. Returns None on failure."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            payload = {
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "10m",
                "options": {
                    "num_ctx": 1024,
                    "num_predict": num_predict,
                    "temperature": 0.2,
                },
            }
            if system:
                payload["system"] = system

            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json=payload,
            )
            if resp.status_code == 200:
                return resp.json().get("response", "")
            logger.warning("Ollama generation returned HTTP %s", resp.status_code)
    except httpx.TimeoutException:
        logger.warning("Ollama generation timed out after %.1f seconds", timeout)
    except httpx.HTTPError as exc:
        logger.warning("Ollama generation request failed: %s", exc)
    except ValueError as exc:
        logger.warning("Ollama returned an invalid response: %s", exc)
    return None


# ─── AI Use Cases ───────────────────────────────────────────────────────────

async def explain_discrepancy(comparisons: List[Dict[str, Any]]) -> DiscrepancyExplanation:
    """AI Use Case B: Explain discrepancies between submitted and extracted fields."""
    comparison_text = "\n".join(
        f"- {c.get('field', 'Unknown')}: Form value = '{c.get('submitted', 'N/A')}', "
        f"Document value = '{c.get('extracted', 'N/A')}'"
        for c in comparisons
    )

    prompt = f"""Analyze these discrepancies between submitted form values and extracted document values 
for a Fixed Deposit Receipt (FDR) compliance check:

{comparison_text}

Provide:
1. A brief summary of the discrepancies
2. Why these discrepancies matter for compliance
3. What evidence should be inspected
4. Recommended next action

Be factual. Do not accuse anyone of fraud. These are potential data entry errors or document issues that need investigation."""

    ai_response = await _call_ollama(prompt, system="You are a compliance analysis assistant for FDR verification.")

    # Build deterministic explanation even if AI is unavailable
    conflicting = []
    evidence = []
    for c in comparisons:
        if c.get("submitted") != c.get("extracted"):
            conflicting.append({
                "field": c.get("field", "Unknown"),
                "submitted": c.get("submitted"),
                "extracted": c.get("extracted"),
            })
            evidence.append(f"Review the {c.get('field', 'field')} on the original certificate")

    summary = ai_response or f"Found {len(conflicting)} field(s) with differences between submitted form data and document extraction."

    return DiscrepancyExplanation(
        summary=summary,
        conflicting_fields=conflicting,
        why_it_matters="Mismatches between submitted values and document evidence may indicate data entry errors, "
                       "outdated documents, or require further verification before the FDR can be approved.",
        evidence_to_inspect=evidence or ["Review the uploaded FDR certificate"],
        recommended_action="Request the institution to verify the discrepant values and re-upload the document if necessary."
    )


async def summarize_case(fdr: FDRInstrument, audit_events: List[AuditEvent]) -> CaseSummary:
    """AI Use Case F: Generate a case summary from record fields and audit trail."""
    important_dates = {
        "issue_date": str(fdr.issue_date) if fdr.issue_date else "N/A",
        "maturity_date": str(fdr.maturity_date) if fdr.maturity_date else "N/A",
        "submitted_at": str(fdr.created_at) if fdr.created_at else "N/A",
    }

    unresolved = []
    if fdr.has_potential_duplicate:
        unresolved.append("Potential duplicate flag is active")
    if fdr.verification_status == VerificationStatus.PENDING:
        unresolved.append("Verification is still pending")
    if fdr.status == FDRStatus.CORRECTION_REQUESTED:
        unresolved.append("Corrections have been requested")
    if fdr.review_priority_score > 50:
        unresolved.append(f"High review priority score: {fdr.review_priority_score}")

    actions = []
    for event in audit_events[:10]:
        actions.append(f"{event.action} by {event.role} at {event.timestamp}")

    # Determine next step
    next_step = "No action required"
    if fdr.status == FDRStatus.SUBMITTED:
        next_step = "Document extraction and validation needed"
    elif fdr.status == FDRStatus.VALIDATED:
        next_step = "Reviewer verification required"
    elif fdr.status == FDRStatus.CORRECTION_REQUESTED:
        next_step = "Institution must address correction requests"
    elif fdr.status == FDRStatus.UNDER_REVIEW:
        next_step = "Awaiting reviewer decision"
    elif fdr.status == FDRStatus.ACTIVE:
        days = (fdr.maturity_date - date.today()).days if fdr.maturity_date else 999
        if days <= 30:
            next_step = f"FDR matures in {days} days — plan for renewal"
        else:
            next_step = "Active and verified — monitor for maturity"

    # Try AI narrative
    ai_narrative = None
    context = (
        f"FDR {fdr.internal_reference}: Status={fdr.status.value}, "
        f"Bank={fdr.bank_name}, Amount={fdr.deposit_amount} {fdr.currency}, "
        f"Issue={fdr.issue_date}, Maturity={fdr.maturity_date}, "
        f"Verification={fdr.verification_status.value}, "
        f"Priority Score={fdr.review_priority_score}, "
        f"Duplicate Flag={fdr.has_potential_duplicate}"
    )
    ai_response = await _call_ollama(
        f"Summarize this FDR compliance case in 2-3 sentences:\n{context}",
        system="You are a compliance case summarizer. Be concise and factual."
    )
    if ai_response:
        ai_narrative = ai_response

    return CaseSummary(
        fdr_reference=fdr.internal_reference,
        current_status=fdr.status.value,
        verification_status=fdr.verification_status.value,
        important_dates=important_dates,
        unresolved_issues=unresolved,
        previous_actions=actions,
        pending_next_step=next_step,
        ai_narrative=ai_narrative,
    )


async def handle_assistant_query(
    query: str,
    user: User,
    db: AsyncSession,
) -> AssistantResponse:
    """AI Use Case E: Natural-language assistant with controlled database queries."""
    query_lower = query.lower().strip()

    # ─── Pattern matching for supported queries ──────────────────────────
    # Maturity queries
    if any(kw in query_lower for kw in ["matur", "expir", "due soon", "upcoming"]):
        days_match = re.search(r"(\d+)\s*days?", query_lower)
        days = int(days_match.group(1)) if days_match else 30
        return await _query_maturing_fdrs(user, db, days)

    # Flagged / duplicate queries
    if any(kw in query_lower for kw in ["duplicate", "flagged", "flag"]):
        return await _query_duplicates(user, db)

    # Pending / awaiting verification
    if any(kw in query_lower for kw in ["pending", "awaiting", "verification", "unverified"]):
        return await _query_pending_verification(user, db)

    # Overdue / long-pending
    if any(kw in query_lower for kw in ["overdue", "pending review", "pending more than", "stale"]):
        days_match = re.search(r"(\d+)\s*days?", query_lower)
        days = int(days_match.group(1)) if days_match else 7
        return await _query_overdue_reviews(user, db, days)

    # Specific FDR lookup
    fdr_ref_match = re.search(r"FDR-\d{4}-\d{4}", query, re.IGNORECASE)
    if fdr_ref_match:
        return await _query_specific_fdr(user, db, fdr_ref_match.group(0))

    # Status summary
    if any(kw in query_lower for kw in ["summary", "overview", "status", "how many"]):
        return await _query_status_summary(user, db)

    # Fallback: Try Ollama for general questions
    ai_response = await _call_ollama(
        f"The user asked: '{query}'\n\n"
        "You are an assistant for the FDR Intelligence & Compliance Portal. "
        "If this is about FDR data, explain that you can answer questions about "
        "maturing FDRs, pending verifications, duplicates, overdue reviews, and specific FDR records. "
        "If it's a general compliance question, provide a helpful answer.",
        system="You are the FDR Portal AI Assistant."
    )

    return AssistantResponse(
        answer=ai_response or (
            "I can help you with:\n"
            "• **Maturing FDRs**: 'Which FDRs mature in the next 30 days?'\n"
            "• **Pending verification**: 'Which records are awaiting verification?'\n"
            "• **Duplicates**: 'Show potential duplicate FDR submissions'\n"
            "• **Overdue reviews**: 'Which cases have been pending for more than 7 days?'\n"
            "• **Specific FDR**: 'Summarize the lifecycle of FDR-2026-0001'\n"
            "• **Overview**: 'Show me a status summary'"
        ),
        query_type="general",
        ai_generated=ai_response is not None,
    )


# ─── Query Functions (Role-scoped) ──────────────────────────────────────────

async def _get_institution_filter(user: User, db: AsyncSession):
    """Get institution ID filter for institution users."""
    if user.role == UserRole.INSTITUTION_USER:
        from app.models.user_institution_role import UserInstitutionRole
        stmt = select(UserInstitutionRole.institution_id).where(
            UserInstitutionRole.user_id == user.id
        )
        result = await db.execute(stmt)
        inst_id = result.scalar()
        return inst_id
    return None


async def _query_maturing_fdrs(user: User, db: AsyncSession, days: int) -> AssistantResponse:
    today = date.today()
    deadline = today + timedelta(days=days)

    conditions = [
        FDRInstrument.maturity_date <= deadline,
        FDRInstrument.maturity_date >= today,
        FDRInstrument.status.notin_([FDRStatus.RELEASED, FDRStatus.REJECTED]),
    ]

    inst_id = await _get_institution_filter(user, db)
    if inst_id:
        conditions.append(FDRInstrument.institution_id == inst_id)

    stmt = (
        select(FDRInstrument)
        .options(selectinload(FDRInstrument.institution))
        .where(*conditions)
        .order_by(FDRInstrument.maturity_date)
    )
    result = await db.execute(stmt)
    fdrs = result.scalars().all()

    records = []
    lines = []
    for f in fdrs:
        days_left = (f.maturity_date - today).days
        records.append({
            "id": str(f.id),
            "reference": f.internal_reference,
            "institution": f.institution.name if f.institution else "N/A",
            "bank": f.bank_name,
            "amount": str(f.deposit_amount),
            "maturity_date": str(f.maturity_date),
            "days_until_maturity": days_left,
        })
        lines.append(
            f"• **{f.internal_reference}** — {f.bank_name}, ₹{f.deposit_amount:,.2f}, "
            f"matures on {f.maturity_date} ({days_left} days)"
        )

    answer = f"**{len(fdrs)} FDR(s) maturing within the next {days} days:**\n\n" + "\n".join(lines) if lines else \
        f"No FDRs maturing within the next {days} days."

    return AssistantResponse(answer=answer, source_records=records, query_type="maturity")


async def _query_duplicates(user: User, db: AsyncSession) -> AssistantResponse:
    conditions = [FDRInstrument.has_potential_duplicate == True]
    inst_id = await _get_institution_filter(user, db)
    if inst_id:
        conditions.append(FDRInstrument.institution_id == inst_id)

    stmt = (
        select(FDRInstrument)
        .options(selectinload(FDRInstrument.institution))
        .where(*conditions)
    )
    result = await db.execute(stmt)
    fdrs = result.scalars().all()

    records = []
    lines = []
    for f in fdrs:
        records.append({
            "id": str(f.id),
            "reference": f.internal_reference,
            "institution": f.institution.name if f.institution else "N/A",
            "fdr_number": f.fdr_number,
            "bank": f.bank_name,
        })
        lines.append(f"• **{f.internal_reference}** — {f.bank_name}, FDR# {f.fdr_number}")

    answer = f"**{len(fdrs)} FDR(s) flagged as potential duplicates:**\n\n" + "\n".join(lines) if lines else \
        "No FDRs currently flagged as potential duplicates."

    return AssistantResponse(answer=answer, source_records=records, query_type="duplicates")


async def _query_pending_verification(user: User, db: AsyncSession) -> AssistantResponse:
    conditions = [FDRInstrument.verification_status == VerificationStatus.PENDING]
    inst_id = await _get_institution_filter(user, db)
    if inst_id:
        conditions.append(FDRInstrument.institution_id == inst_id)

    stmt = (
        select(FDRInstrument)
        .options(selectinload(FDRInstrument.institution))
        .where(*conditions)
        .order_by(FDRInstrument.created_at)
    )
    result = await db.execute(stmt)
    fdrs = result.scalars().all()

    records = []
    lines = []
    for f in fdrs:
        records.append({
            "id": str(f.id),
            "reference": f.internal_reference,
            "status": f.status.value,
            "institution": f.institution.name if f.institution else "N/A",
        })
        lines.append(f"• **{f.internal_reference}** — {f.status.value}, {f.institution.name if f.institution else 'N/A'}")

    answer = f"**{len(fdrs)} FDR(s) awaiting verification:**\n\n" + "\n".join(lines) if lines else \
        "All FDRs have been verified."

    return AssistantResponse(answer=answer, source_records=records, query_type="pending_verification")


async def _query_overdue_reviews(user: User, db: AsyncSession, days: int) -> AssistantResponse:
    from datetime import datetime, timedelta as td
    cutoff = datetime.utcnow() - td(days=days)

    conditions = [
        FDRInstrument.status.in_([FDRStatus.SUBMITTED, FDRStatus.UNDER_REVIEW, FDRStatus.VALIDATED]),
        FDRInstrument.updated_at <= cutoff,
    ]
    inst_id = await _get_institution_filter(user, db)
    if inst_id:
        conditions.append(FDRInstrument.institution_id == inst_id)

    stmt = (
        select(FDRInstrument)
        .options(selectinload(FDRInstrument.institution))
        .where(*conditions)
    )
    result = await db.execute(stmt)
    fdrs = result.scalars().all()

    records = []
    lines = []
    for f in fdrs:
        records.append({
            "id": str(f.id),
            "reference": f.internal_reference,
            "status": f.status.value,
            "last_updated": str(f.updated_at),
        })
        lines.append(f"• **{f.internal_reference}** — {f.status.value}, last updated {f.updated_at}")

    answer = f"**{len(fdrs)} FDR(s) pending review for more than {days} days:**\n\n" + "\n".join(lines) if lines else \
        f"No FDRs pending review for more than {days} days."

    return AssistantResponse(answer=answer, source_records=records, query_type="overdue_reviews")


async def _query_specific_fdr(user: User, db: AsyncSession, reference: str) -> AssistantResponse:
    stmt = (
        select(FDRInstrument)
        .options(selectinload(FDRInstrument.institution))
        .where(FDRInstrument.internal_reference.ilike(reference))
    )
    result = await db.execute(stmt)
    fdr = result.scalars().first()

    if not fdr:
        return AssistantResponse(
            answer=f"No FDR found with reference '{reference}'.",
            query_type="specific_fdr"
        )

    # Check access
    inst_id = await _get_institution_filter(user, db)
    if inst_id and fdr.institution_id != inst_id:
        return AssistantResponse(
            answer="You do not have permission to access this FDR record.",
            query_type="access_denied"
        )

    days_to_mat = (fdr.maturity_date - date.today()).days if fdr.maturity_date else None

    answer = (
        f"**{fdr.internal_reference}** — {fdr.institution.name if fdr.institution else 'N/A'}\n\n"
        f"• **Status**: {fdr.status.value}\n"
        f"• **Verification**: {fdr.verification_status.value}\n"
        f"• **Bank**: {fdr.bank_name} ({fdr.branch_name or 'N/A'})\n"
        f"• **FDR Number**: {fdr.fdr_number}\n"
        f"• **Amount**: ₹{fdr.deposit_amount:,.2f} {fdr.currency}\n"
        f"• **Issue Date**: {fdr.issue_date}\n"
        f"• **Maturity Date**: {fdr.maturity_date}"
        + (f" ({days_to_mat} days)" if days_to_mat is not None else "") + "\n"
        f"• **Review Priority**: {fdr.review_priority_score}/100\n"
        f"• **Duplicate Flag**: {'⚠️ Yes' if fdr.has_potential_duplicate else '✅ No'}"
    )

    return AssistantResponse(
        answer=answer,
        source_records=[{
            "id": str(fdr.id),
            "reference": fdr.internal_reference,
            "status": fdr.status.value,
        }],
        query_type="specific_fdr"
    )


async def _query_status_summary(user: User, db: AsyncSession) -> AssistantResponse:
    conditions = []
    inst_id = await _get_institution_filter(user, db)
    if inst_id:
        conditions.append(FDRInstrument.institution_id == inst_id)

    # Count by status
    stmt = select(
        FDRInstrument.status,
        func.count(FDRInstrument.id)
    ).group_by(FDRInstrument.status)
    if conditions:
        stmt = stmt.where(*conditions)

    result = await db.execute(stmt)
    status_counts = {row[0].value: row[1] for row in result.all()}

    total = sum(status_counts.values())
    lines = [f"• **{status}**: {count}" for status, count in sorted(status_counts.items())]

    answer = f"**FDR Status Summary ({total} total):**\n\n" + "\n".join(lines)

    return AssistantResponse(
        answer=answer,
        source_records=[{"status_distribution": status_counts}],
        query_type="status_summary"
    )
