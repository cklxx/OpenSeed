"""ArXiv watch model."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ArxivWatch(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    query: str
    since_year: int | None = None
    last_run: datetime | None = None
