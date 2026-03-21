"""Tests for the rewritten ResearchAssistant."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from openseed.agent.assistant import ResearchAssistant, _build_prompt
from openseed.models.paper import Author, Paper
from openseed.storage.library import PaperLibrary


@pytest.fixture
def lib(tmp_path):
    return PaperLibrary(tmp_path / "library")


@pytest.fixture
def assistant(lib):
    return ResearchAssistant(library=lib, model="test-model", session_id="sess-1")


def test_build_prompt_with_context_and_history():
    result = _build_prompt(
        "<context>data</context>",
        [{"user": "Q1", "assistant": "A1"}],
        "Q2",
    )
    assert "<context>data</context>" in result
    assert "User: Q1" in result
    assert "Assistant: A1" in result
    assert result.endswith("Q2")


def test_build_prompt_no_context():
    result = _build_prompt("", [], "Q1")
    assert result == "Q1"


@patch("openseed.agent.assistant._ask")
def test_ask_returns_answer_and_saves_history(mock_ask, assistant):
    mock_ask.return_value = "The answer is 42."
    answer = assistant.ask("What is the answer?")
    assert answer == "The answer is 42."
    assert len(assistant._history) == 1
    assert assistant._history[0]["user"] == "What is the answer?"
    assert assistant._history[0]["assistant"] == "The answer is 42."


@patch("openseed.agent.assistant._ask")
def test_ask_accumulates_history(mock_ask, assistant):
    mock_ask.return_value = "A1"
    assistant.ask("Q1")
    mock_ask.return_value = "A2"
    assistant.ask("Q2")
    assert len(assistant._history) == 2


@patch("openseed.agent.assistant._ask")
def test_clear_history(mock_ask, assistant):
    mock_ask.return_value = "A1"
    assistant.ask("Q1")
    assistant.clear_history()
    assert assistant._history == []


@patch("openseed.agent.assistant._stream")
def test_stream_yields_chunks_and_saves(mock_stream, assistant):
    mock_stream.return_value = iter(["Hello, ", "world!"])
    chunks = list(assistant.stream("greet me"))
    assert chunks == ["Hello, ", "world!"]
    assert len(assistant._history) == 1
    assert assistant._history[0]["assistant"] == "Hello, world!"


@patch("openseed.agent.assistant._ask")
def test_review_paper(mock_ask, assistant):
    mock_ask.return_value = "## Review\nGood paper."
    paper = Paper(
        title="Test Paper",
        authors=[Author(name="Alice")],
        abstract="An abstract.",
    )
    result = assistant.review_paper(paper)
    assert "Review" in result
    assert mock_ask.called


@patch("openseed.agent.assistant._ask")
def test_get_debug_info(mock_ask, assistant):
    mock_ask.return_value = "answer"
    assistant.ask("Q")
    info = assistant.get_debug_info()
    assert "papers_found" in info


@patch("openseed.agent.assistant._ask")
def test_memory_saved_to_db(mock_ask, lib):
    assistant = ResearchAssistant(library=lib, model="test", session_id="mem-test")
    mock_ask.return_value = "response"
    assistant.ask("question")
    from openseed.agent.memory import MemoryStore

    store = MemoryStore(lib)
    entries = store.get_session_history("mem-test")
    assert len(entries) == 2
    assert entries[0].role == "user"
    assert entries[1].role == "assistant"
