"""Watch models for paper discovery sources."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ArxivWatch(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    query: str
    since_year: int | None = None
    last_run: datetime | None = None
    source: Literal["arxiv", "rss"] = "arxiv"
    feed_url: str | None = None
