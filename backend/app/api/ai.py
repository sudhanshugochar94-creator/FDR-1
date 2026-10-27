"""AI endpoints for Ollama integration, discrepancy explanations, case summaries, and assistant queries."""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ensure_fdr_institution_access, get_current_user
from app.core.exceptions import NotFoundException
from app.database import get_db
from app.models.audit import AuditEvent
from app.models.agent_run import FDRAgentRun
from app.models.fdr import FDRInstrument
from app.models.user import User
from app.services.ai_service import (
    AIHealthResponse,
    AssistantResponse,
    CaseSummary,
    DiscrepancyExplanation,
    check_ollama_health,
    explain_discrepancy,
    handle_assistant_query,
    summarize_case,
)
from app.services.agent_service import (
    AGENT_CATALOG,
    AgentRunResponse,
    run_fdr_agent_workflow,
    serialize_agent_run,
)

router = APIRouter(prefix="/ai", tags=["AI Intelligence"])


@router.get("/health", response_model=AIHealthResponse)
async def ai_health_check():
    """Check Ollama connectivity and model availability."""
    return await check_ollama_health()


@router.get("/agents/catalog", dependencies=[Depends(get_current_user)])
async def agent_catalog():
    """Describe which workflow-agent capabilities are implemented versus planned."""
    return AGENT_CATALOG


@router.post("/agents/{fdr_id}/run", response_model=AgentRunResponse)
async def run_agents_endpoint(
    fdr_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run the recommend-only agent workflow for a single authorized FDR."""
    fdr = (await db.execute(select(FDRInstrument).where(FDRInstrument.id == fdr_id))).scalars().first()
    if not fdr:
        raise NotFoundException(f"FDR {fdr_id} not found")
    await ensure_fdr_institution_access(fdr=fdr, user=current_user, db=db)

    run = await run_fdr_agent_workflow(fdr=fdr, user=current_user, db=db)
    await db.commit()
    await db.refresh(run)
    return serialize_agent_run(run)


@router.get("/agents/{fdr_id}/runs", response_model=List[AgentRunResponse])
async def list_agent_runs_endpoint(
    fdr_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List recent agent recommendations for an authorized FDR."""
    fdr = (await db.execute(select(FDRInstrument).where(FDRInstrument.id == fdr_id))).scalars().first()
    if not fdr:
        raise NotFoundException(f"FDR {fdr_id} not found")
    await ensure_fdr_institution_access(fdr=fdr, user=current_user, db=db)

    stmt = (
        select(FDRAgentRun)
        .where(FDRAgentRun.fdr_instrument_id == fdr_id)
        .order_by(FDRAgentRun.created_at.desc())
        .limit(10)
    )
    runs = (await db.execute(stmt)).scalars().all()
    return [serialize_agent_run(run) for run in runs]


class DiscrepancyRequest(BaseModel):
    comparisons: List[Dict[str, Any]] = Field(
        ...,
        description="List of field comparisons, each with 'field', 'submitted', 'extracted'",
        min_length=1,
    )


@router.post("/explain-discrepancy", response_model=DiscrepancyExplanation)
async def explain_discrepancy_endpoint(
    payload: DiscrepancyRequest,
    current_user: User = Depends(get_current_user),
):
    """AI Use Case B: Explain discrepancies between submitted and extracted FDR fields."""
    return await explain_discrepancy(payload.comparisons)


class SummarizeCaseRequest(BaseModel):
    fdr_id: UUID


@router.post("/summarize-case", response_model=CaseSummary)
async def summarize_case_endpoint(
    payload: SummarizeCaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI Use Case F: Generate a comprehensive case summary for an FDR record."""
    stmt = select(FDRInstrument).where(FDRInstrument.id == payload.fdr_id)
    fdr = (await db.execute(stmt)).scalars().first()
    if not fdr:
        raise NotFoundException(f"FDR {payload.fdr_id} not found")
    await ensure_fdr_institution_access(fdr=fdr, user=current_user, db=db)

    # Fetch audit events for this FDR
    audit_stmt = (
        select(AuditEvent)
        .where(AuditEvent.entity_id == payload.fdr_id)
        .order_by(AuditEvent.timestamp.desc())
        .limit(20)
    )
    audit_events = (await db.execute(audit_stmt)).scalars().all()

    return await summarize_case(fdr, list(audit_events))


class AssistantRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)


@router.post("/assistant", response_model=AssistantResponse)
async def ai_assistant_endpoint(
    payload: AssistantRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI Use Case E: Natural-language assistant for FDR queries."""
    return await handle_assistant_query(payload.query, current_user, db)
