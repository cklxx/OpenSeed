"""ResearchSession — a saved autonomous research run."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ResearchSession(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    topic: str
    query_variants: list[str] = []
    paper_ids: list[str] = []
    synthesis: str = ""
    report: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
