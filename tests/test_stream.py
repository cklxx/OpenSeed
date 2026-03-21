"""Tests for streaming infrastructure in reader.py."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from openseed.agent.reader import _stream, _stream_async


def _make_assistant_msg(text_chunks: list[str]):
    """Build a fake AssistantMessage with TextBlock content."""
    from claude_agent_sdk.types import AssistantMessage, TextBlock

    blocks = [TextBlock(text=t) for t in text_chunks]
    return AssistantMessage(content=blocks, model="test")


def _make_tool_msg(name: str, inp: dict):
    """Build a fake AssistantMessage with a ToolUseBlock."""
    from claude_agent_sdk.types import AssistantMessage, ToolUseBlock

    block = ToolUseBlock(id="t1", name=name, input=inp)
    return AssistantMessage(content=[block], model="test")


async def _fake_query_texts(prompt, options):
    """Async generator yielding two AssistantMessages with text."""
    yield _make_assistant_msg(["Hello, "])
    yield _make_assistant_msg(["world!"])


async def _fake_query_mixed(prompt, options):
    """Async generator with text + tool use blocks."""
    yield _make_tool_msg("WebSearch", {"query": "transformers"})
    yield _make_assistant_msg(["Answer: yes"])


@pytest.mark.asyncio
async def test_stream_async_yields_text_blocks():
    with patch("openseed.agent.reader.query", side_effect=_fake_query_texts):
        chunks = [c async for c in _stream_async("model", "system", "prompt")]
    assert chunks == ["Hello, ", "world!"]


@pytest.mark.asyncio
async def test_stream_async_calls_on_step_for_tool_use():
    steps = []
    with patch("openseed.agent.reader.query", side_effect=_fake_query_mixed):
        chunks = [c async for c in _stream_async("model", "system", "prompt", on_step=steps.append)]
    assert chunks == ["Answer: yes"]
    assert len(steps) == 1
    assert "WebSearch" in steps[0]


def test_stream_sync_bridge():
    with patch("openseed.agent.reader.query", side_effect=_fake_query_texts):
        chunks = list(_stream("model", "system", "prompt"))
    assert chunks == ["Hello, ", "world!"]


def test_stream_sync_empty():
    async def _empty(prompt, options):
        return
        yield  # noqa: UP039 — unreachable yield makes this an async generator

    with patch("openseed.agent.reader.query", side_effect=_empty):
        chunks = list(_stream("model", "system", "prompt"))
    assert chunks == []
