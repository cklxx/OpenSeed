"""openMax monitoring integration — usage and memory (optional, degrades gracefully)."""

from __future__ import annotations

import uuid
from pathlib import Path

_PREFIX = "openseed"


def make_usage_recorder(op_name: str) -> object:
    """Return a callback that records ResultMessage usage to openMax UsageStore.

    Usage: pass as on_result= to _ask(). Safe to call even if openMax is missing.
    """

    def _record(result_msg: object) -> None:
        try:
            from openmax.usage import UsageStore, usage_from_result

            session_id = f"{_PREFIX}_{op_name}_{uuid.uuid4().hex[:8]}"
            UsageStore().save(usage_from_result(session_id, result_msg))
        except Exception:
            pass

    return _record


def record_research_lesson(topic: str, lesson: str, cwd: str | None = None) -> None:
    """Persist a research insight to openMax MemoryStore."""
    try:
        from openmax.memory.store import MemoryStore

        MemoryStore().record_lesson(
            cwd=cwd or str(Path.home()),
            task=f"research: {topic}",
            lesson=lesson,
            source="openseed",
        )
    except Exception:
        pass


def get_usage_summary(limit: int = 50) -> str | None:
    """Aggregate openseed-tagged sessions from openMax UsageStore."""
    try:
        from openmax.usage import UsageStore

        store = UsageStore()
        records = [r for r in store.list_all(limit=200) if r.session_id.startswith(_PREFIX)]
        if not records:
            return None
        agg = store.aggregate(records[:limit])
        return f"[{len(records)} ops] {agg.summary_line()}"
    except Exception:
        return None
