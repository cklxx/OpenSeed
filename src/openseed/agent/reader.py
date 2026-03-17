"""Claude-powered paper reader."""

from __future__ import annotations

import anthropic
from pydantic import BaseModel


class PaperSummary(BaseModel):
    title: str
    one_liner: str  # one sentence
    key_contributions: list[str]  # 3-5 bullets
    methodology: str
    limitations: str
    relevance_score: int  # 1-10


class PaperAnalysis(BaseModel):
    summary: PaperSummary
    key_findings: list[str]
    open_questions: list[str]
    related_topics: list[str]


class PaperReader:
    """Reads and analyzes papers using Claude."""

    def __init__(self, model: str = "claude-opus-4-6") -> None:
        self._client = anthropic.Anthropic()
        self._model = model

    def _ask(self, system: str, prompt: str) -> str:
        """Internal helper: stream a response and return the full text."""
        with self._client.messages.stream(
            model=self._model,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            return stream.get_final_message().content[-1].text

    def summarize_paper(self, text: str) -> PaperSummary:
        """Generate a structured summary of a paper."""
        response = self._client.beta.messages.parse(
            model=self._model,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system="You are a research paper summarizer. Extract structured information.",
            messages=[{"role": "user", "content": f"Summarize the following paper:\n\n{text}"}],
            output_format=PaperSummary,
        )
        return response.parsed

    def extract_key_findings(self, text: str) -> list[str]:
        """Extract key findings from a paper."""
        with self._client.messages.stream(
            model=self._model,
            max_tokens=2048,
            thinking={"type": "adaptive"},
            system="You are a research analyst. Extract key findings as a numbered list.",
            messages=[{"role": "user", "content": f"Extract the key findings:\n\n{text}"}],
        ) as stream:
            result = stream.get_final_message().content[-1].text
        return [line.strip() for line in result.strip().split("\n") if line.strip()]

    def analyze_paper(self, text: str) -> PaperAnalysis:
        """Perform full structured analysis of a paper."""
        response = self._client.beta.messages.parse(
            model=self._model,
            max_tokens=8096,
            thinking={"type": "adaptive"},
            system="You are an expert research analyst. Provide a comprehensive analysis.",
            messages=[{"role": "user", "content": f"Analyze the following paper:\n\n{text}"}],
            output_format=PaperAnalysis,
        )
        return response.parsed

    def generate_questions(self, text: str) -> list[str]:
        """Generate research questions based on a paper."""
        with self._client.messages.stream(
            model=self._model,
            max_tokens=2048,
            thinking={"type": "adaptive"},
            system="You are a research advisor. Generate insightful questions about this paper.",
            messages=[{"role": "user", "content": f"Generate research questions about:\n\n{text}"}],
        ) as stream:
            result = stream.get_final_message().content[-1].text
        return [line.strip() for line in result.strip().split("\n") if line.strip()]
