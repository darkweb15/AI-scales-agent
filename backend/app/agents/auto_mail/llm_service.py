"""LLMService interface and StubLLMService.

Abstracts the LLM backend (OpenAI, Anthropic, local Ollama, etc.)
so the AutoMailAgent can be tested without real API calls.
"""

from __future__ import annotations

import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)


class LLMService:
    """Abstract interface for LLM-based content personalization."""

    def personalize(self, template: str, context: Dict[str, str]) -> str:
        """Replace template variables with context values using LLM.

        Parameters
        ----------
        template:
            Text containing {variable} placeholders.
        context:
            Dictionary mapping variable names to values.

        Returns
        -------
        Personalized text with all placeholders resolved.
        """
        raise NotImplementedError


class StubLLMService(LLMService):
    """In-memory stub that replaces {variable} placeholders with context values.

    Useful for unit tests and local development.
    """

    def personalize(self, template: str, context: Dict[str, str]) -> str:
        """Replace all {variable} placeholders with values from context.

        If a placeholder is not found in context, it is replaced with an empty string.
        """
        result = template
        
        # Find all {variable} patterns
        placeholders = re.findall(r'\{(\w+)\}', template)
        
        for placeholder in placeholders:
            value = context.get(placeholder, "")
            result = result.replace(f"{{{placeholder}}}", value)
        
        logger.debug("StubLLMService: personalized template with %d placeholders", len(placeholders))
        return result
