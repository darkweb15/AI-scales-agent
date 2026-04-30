"""NLP Engine interface and stub implementation.

In production this would call an LLM service (OpenAI, Anthropic, etc.)
to extract intent from call transcripts.
"""

from __future__ import annotations

from app.models.enums import Intent


class NLPEngine:
    """Abstract interface for NLP operations."""

    def extract_intent(self, transcript: str) -> Intent:
        """Classify the dominant intent in *transcript*."""
        raise NotImplementedError

    def get_confidence_score(self, intent: Intent) -> float:
        """Return a confidence score in [0.0, 1.0] for the given intent."""
        raise NotImplementedError


class StubNLPEngine(NLPEngine):
    """Deterministic stub for testing.

    Returns the intent and confidence set at construction time.
    """

    def __init__(
        self,
        intent: Intent = Intent.unknown,
        confidence: float = 0.9,
    ) -> None:
        self._intent = intent
        self._confidence = confidence

    def extract_intent(self, transcript: str) -> Intent:
        return self._intent

    def get_confidence_score(self, intent: Intent) -> float:
        return self._confidence
