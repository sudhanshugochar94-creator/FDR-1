import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text

from app.database import Base
from app.models.sql_types import JSONB, UUID


class FDRAgentRun(Base):
    __tablename__ = "fdr_agent_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fdr_instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("fdr_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_results = Column(JSONB, nullable=False)
    ai_summary = Column(Text, nullable=False)
    ai_generated = Column(Boolean, nullable=False, default=False)
    ai_model = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
