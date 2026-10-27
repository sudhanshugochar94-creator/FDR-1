from sqlalchemy import JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB as PostgreSQLJSONB

UUID = Uuid
JSONB = JSON().with_variant(PostgreSQLJSONB, "postgresql")
