import json
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.audit import AuditEvent
from app.models.agent_run import FDRAgentRun
from app.models.document import DocumentUploadType, FDRDocument
from app.models.duplicate import DuplicateCandidate
from app.models.extraction import ExtractionResult
from app.models.fdr import FDRInstrument
from app.models.lifecycle import ReleaseRequest, RenewalRequest
from app.models.user import User
from app.models.validation import FindingSeverity, ValidationFinding
from app.models.verification import VerificationRecord
from app.services.ai_service import _call_ollama


class AgentResult(BaseModel):
    agent_id: str
    name: str
    status: str
    findings: List[str]
    recommendations: List[str]
    evidence: List[str]
    human_approval_required: bool = True
    simulated: bool = False


class AgentRunResponse(BaseModel):
    id: UUID
    fdr_id: UUID
    agents: List[AgentResult]
    ai_summary: str
    ai_generated: bool
    ai_model: Optional[str]
    human_approval_required: bool = True
    created_at: datetime


AGENT_CATALOG = [
    {
        "id": "intake",
        "name": "FDR Intake Agent",
        "implemented": True,
        "implemented_features": ["Checks for an uploaded original FDR document and records its file fingerprint."],
        "planned_features": ["Configurable institution-specific required document policies."],
    },
    {
        "id": "document",
        "name": "Document Intelligence Agent",
        "implemented": True,
        "implemented_features": ["Uses the existing text/OCR extraction and flags missing or low-confidence extracted fields."],
        "planned_features": ["Human correction of extracted fields and broader document layouts."],
    },
    {
        "id": "duplicate",
        "name": "Duplicate Detection Agent",
        "implemented": True,
        "implemented_features": ["Reports matches found by existing FDR-number, bank/amount/date, and document-hash rules."],
        "planned_features": ["Institution-configurable matching thresholds."],
    },
    {
        "id": "compliance",
        "name": "Compliance & Risk Analysis Agent",
        "implemented": True,
        "implemented_features": ["Summarizes persisted deterministic validation findings and current review priority."],
        "planned_features": ["Additional institution-approved compliance rules."],
    },
    {
        "id": "verification",
        "name": "Verification Workflow Agent",
        "implemented": True,
        "implemented_features": ["Builds an evidence-based checklist and recommends the existing manual review route."],
        "planned_features": ["Approved bank integrations; none are connected in this prototype."],
    },
    {
        "id": "lifecycle",
        "name": "Lifecycle Monitoring Agent",
        "implemented": True,
        "implemented_features": ["Reports maturity timing and existing renewal/release requests when a run is requested."],
        "planned_features": ["Scheduled reminders and automatic escalations."],
    },
    {
        "id": "case-summary",
        "name": "Audit & Case Summary Agent",
        "implemented": True,
        "implemented_features": ["Summarizes recent audit evidence; Ollama may produce a clearly labelled narrative."],
        "planned_features": ["Searchable cross-case evidence summaries."],
    },
]


def _result(
    agent_id: str,
    name: str,
    findings: List[str],
    recommendations: List[str],
    evidence: List[str],
    status: str = "review",
    simulated: bool = False,
) -> AgentResult:
    return AgentResult(
        agent_id=agent_id,
        name=name,
        status=status,
        findings=findings,
        recommendations=recommendations,
        evidence=evidence,
        simulated=simulated,
    )


async def run_fdr_agent_workflow(
    fdr: FDRInstrument,
    user: User,
    db: AsyncSession,
    generate_ai_summary: bool = True,
) -> FDRAgentRun:
    documents = list(
        (
            await db.execute(
                select(FDRDocument)
                .where(FDRDocument.fdr_instrument_id == fdr.id)
                .order_by(FDRDocument.created_at.desc())
            )
        ).scalars().all()
    )
    extractions = list(
        (
            await db.execute(
                select(ExtractionResult)
                .join(FDRDocument, ExtractionResult.document_id == FDRDocument.id)
                .where(FDRDocument.fdr_instrument_id == fdr.id)
                .order_by(ExtractionResult.created_at.desc())
            )
        ).scalars().all()
    )
    findings = list(
        (
            await db.execute(
                select(ValidationFinding)
                .where(ValidationFinding.fdr_instrument_id == fdr.id)
                .order_by(ValidationFinding.created_at.desc())
            )
        ).scalars().all()
    )
    duplicates = list(
        (
            await db.execute(
                select(DuplicateCandidate).where(
                    or_(
                        DuplicateCandidate.fdr_instrument_a_id == fdr.id,
                        DuplicateCandidate.fdr_instrument_b_id == fdr.id,
                    )
                )
            )
        ).scalars().all()
    )
    verifications = list(
        (
            await db.execute(
                select(VerificationRecord)
                .where(VerificationRecord.fdr_instrument_id == fdr.id)
                .order_by(VerificationRecord.created_at.desc())
            )
        ).scalars().all()
    )
    renewals = list(
        (
            await db.execute(
                select(RenewalRequest).where(RenewalRequest.original_fdr_id == fdr.id)
            )
        ).scalars().all()
    )
    releases = list(
        (
            await db.execute(
                select(ReleaseRequest).where(ReleaseRequest.fdr_instrument_id == fdr.id)
            )
        ).scalars().all()
    )
    audit_events = list(
        (
            await db.execute(
                select(AuditEvent)
                .where(AuditEvent.entity_id == fdr.id)
                .order_by(AuditEvent.timestamp.desc())
                .limit(10)
            )
        ).scalars().all()
    )

    original_documents = [doc for doc in documents if doc.upload_type == DocumentUploadType.ORIGINAL]
    if original_documents:
        intake_findings = ["An original FDR document is on file."]
        intake_evidence = [
            f"{len(original_documents)} original document(s); latest SHA-256 {original_documents[0].file_hash_sha256[:16]}."
        ]
        intake_recommendations = ["Confirm the uploaded original is legible and is the intended certificate."]
        intake_status = "clear"
    else:
        intake_findings = ["No document marked ORIGINAL has been uploaded."]
        intake_evidence = [f"{len(documents)} document(s) uploaded in total."]
        intake_recommendations = ["Upload the original FDR document before manual verification."]
        intake_status = "attention"

    latest_extraction = extractions[0] if extractions else None
    extracted_fields = (latest_extraction.extracted_fields or {}) if latest_extraction else {}
    confidence_scores = (latest_extraction.confidence_scores or {}) if latest_extraction else {}
    required_fields = ("fdr_number", "bank_name", "deposit_amount", "issue_date", "maturity_date")
    missing_fields = [field for field in required_fields if not extracted_fields.get(field)]
    uncertain_fields = [
        field for field in required_fields
        if field in extracted_fields
        and isinstance(confidence_scores.get(field), (int, float))
        and confidence_scores[field] < 0.8
    ]
    document_findings = []
    if not latest_extraction:
        document_findings.append("No extraction result is available yet.")
    if missing_fields:
        document_findings.append(f"Fields missing from extraction: {', '.join(missing_fields)}.")
    if uncertain_fields:
        document_findings.append(f"Fields with confidence below 0.80: {', '.join(uncertain_fields)}.")
    if not document_findings:
        document_findings.append("All tracked fields were extracted; review the values against the source document.")
    document_status = "attention" if not latest_extraction or missing_fields or uncertain_fields else "review"
    document_result = _result(
        "document",
        "Document Intelligence Agent",
        document_findings,
        ["A person must compare extracted values with the original document; extraction is not proof of authenticity."],
        [
            f"Latest extraction method: {latest_extraction.extraction_method.value}."
            if latest_extraction else "No extraction record."
        ],
        document_status,
    )

    duplicate_findings = [
        f"Candidate match ({candidate.match_score:.0%}) is {candidate.status.value}; reasons: "
        f"{'; '.join(candidate.match_reasons or []) or 'not recorded'}."
        for candidate in duplicates
    ]
    if not duplicate_findings and fdr.has_potential_duplicate:
        duplicate_findings = ["The FDR is flagged as a potential duplicate, but no candidate details are recorded."]
    duplicate_status = (
        "attention"
        if fdr.has_potential_duplicate
        or any(candidate.status.value == "PENDING" for candidate in duplicates)
        else "clear"
    )
    if not duplicate_findings:
        duplicate_findings = ["No duplicate candidates are recorded for this FDR."]
    duplicate_result = _result(
        "duplicate",
        "Duplicate Detection Agent",
        duplicate_findings,
        ["Review each candidate and record a human decision; a match is not itself a duplicate determination."]
        if duplicates else [],
        [f"{len(duplicates)} candidate(s) from existing deterministic duplicate checks."],
        duplicate_status,
    )

    compliance_findings = [
        f"{finding.severity.value}: {finding.field_name} — {finding.description or finding.finding_type.value}"
        for finding in findings
        if finding.severity != FindingSeverity.INFO
    ]
    if not compliance_findings:
        compliance_findings = ["No unresolved warning or critical validation findings are recorded."]
    if fdr.maturity_date < fdr.issue_date:
        compliance_findings.append("Maturity date is earlier than issue date.")
    compliance_status = "attention" if any(
        finding.severity in (FindingSeverity.WARNING, FindingSeverity.CRITICAL)
        for finding in findings
    ) or fdr.maturity_date < fdr.issue_date else "clear"
    compliance_result = _result(
        "compliance",
        "Compliance & Risk Analysis Agent",
        compliance_findings,
        ["Resolve recorded findings through the authorized review workflow; the agent cannot determine compliance or approve the FDR."],
        [
            f"Deterministic review priority: {fdr.review_priority_score}/100.",
            f"{len(findings)} persisted validation finding(s).",
        ],
        compliance_status,
    )

    verification_findings = []
    verification_recommendations = []
    if not documents:
        verification_findings.append("No supporting document is available for manual review.")
        verification_recommendations.append("Obtain and inspect supporting evidence.")
    if fdr.has_potential_duplicate or any(candidate.status.value == "PENDING" for candidate in duplicates):
        verification_findings.append("A potential duplicate requires human review.")
    if any(finding.severity == FindingSeverity.CRITICAL for finding in findings):
        verification_findings.append("Critical validation finding(s) remain recorded.")
    if not verifications:
        verification_recommendations.append("Route to an authorized official for document checks and approved verification.")
    else:
        verification_findings.append(f"{len(verifications)} human verification record(s) exist; latest result is {verifications[0].result.value}.")
    verification_recommendations.append(
        "No bank connection is configured. Any BANK_CONFIRMATION in this prototype is a manually entered record, not a live bank verification."
    )
    verification_result = _result(
        "verification",
        "Verification Workflow Agent",
        verification_findings or ["No blocking checklist items were identified from recorded evidence."],
        verification_recommendations,
        [f"{len(verifications)} verification record(s); {len(documents)} document(s)."],
        "attention" if verification_findings else "review",
    )

    days_to_maturity = (fdr.maturity_date - date.today()).days
    lifecycle_findings = [
        f"Maturity date is {abs(days_to_maturity)} day(s) {'ahead' if days_to_maturity >= 0 else 'past'}."
    ]
    lifecycle_findings.append(f"{len(renewals)} renewal request(s); {len(releases)} release request(s) recorded.")
    lifecycle_recommendations = []
    if days_to_maturity <= 30:
        lifecycle_recommendations.append("Review maturity and decide whether to start the existing renewal or release workflow.")
    if renewals and any(request.status.value == "PENDING" for request in renewals):
        lifecycle_recommendations.append("Review the pending renewal request.")
    if releases and any(request.status.value in ("PENDING", "UNDER_REVIEW") for request in releases):
        lifecycle_recommendations.append("Review the pending release request.")
    lifecycle_result = _result(
        "lifecycle",
        "Lifecycle Monitoring Agent",
        lifecycle_findings,
        lifecycle_recommendations,
        [f"FDR maturity date: {fdr.maturity_date.isoformat()}."],
        "attention" if days_to_maturity <= 30 else "clear",
    )

    case_findings = [
        f"Record status: {fdr.status.value}; verification status: {fdr.verification_status.value}.",
        f"{len(audit_events)} recent audit event(s) available for this FDR.",
    ]
    case_findings.extend(
        f"Recent event: {event.action} ({event.timestamp.isoformat()})."
        for event in audit_events[:5]
    )
    case_result = _result(
        "case-summary",
        "Audit & Case Summary Agent",
        case_findings,
        ["Use the linked audit trail and source documents as the authoritative evidence."],
        [f"Summary is based on {len(audit_events)} recent FDR audit event(s)."],
        "review",
    )

    results = [
        _result("intake", "FDR Intake Agent", intake_findings, intake_recommendations, intake_evidence, intake_status),
        document_result,
        duplicate_result,
        compliance_result,
        verification_result,
        lifecycle_result,
        case_result,
    ]
    prompt_data = [{"agent": result.name, "status": result.status} for result in results]
    narrative = None
    if generate_ai_summary:
        narrative = await _call_ollama(
            "Answer with exactly two sentences using this format: "
            "'Agents requiring human follow-up: [comma-separated agent names whose status is attention]. "
            "An authorized reviewer must review the FDR record; this is not an approval or authenticity decision.' "
            "Use only names whose status is attention in the supplied JSON. If none need attention, write 'None'. "
            "Do not recommend review of an agent.\n"
            + json.dumps(prompt_data, ensure_ascii=True),
            system="You are a formatter, not an analyst. Follow the requested format using only supplied agent names and statuses.",
            timeout=60.0,
            num_predict=128,
        )
    ai_generated = bool(narrative and narrative.strip())
    summary = (
        narrative.strip()
        if ai_generated
        else (
            f"{len(documents)} document(s), {len(findings)} validation finding(s), and "
            f"{len(duplicates)} duplicate candidate(s) are recorded. "
            "Review the checklist and source evidence manually; no approval or authenticity decision was made."
        )
    )
    run = FDRAgentRun(
        fdr_instrument_id=fdr.id,
        requested_by=user.id,
        agent_results=[result.model_dump(mode="json") for result in results],
        ai_summary=summary,
        ai_generated=ai_generated,
        ai_model=settings.OLLAMA_MODEL if ai_generated else None,
    )
    db.add(run)
    await db.flush()
    db.add(
        AuditEvent(
            user_id=user.id,
            role=user.role.value,
            action="AI_AGENT_WORKFLOW_COMPLETED",
            entity_type="FDRInstrument",
            entity_id=fdr.id,
            after_values={
                "agent_run_id": str(run.id),
                "agents": [result.agent_id for result in results],
                "ai_generated": ai_generated,
            },
            reason="Agents produced evidence-based recommendations; human review remains required.",
        )
    )
    await db.flush()
    return run


def serialize_agent_run(run: FDRAgentRun) -> AgentRunResponse:
    return AgentRunResponse(
        id=run.id,
        fdr_id=run.fdr_instrument_id,
        agents=[AgentResult.model_validate(result) for result in run.agent_results],
        ai_summary=run.ai_summary,
        ai_generated=run.ai_generated,
        ai_model=run.ai_model,
        created_at=run.created_at,
    )
