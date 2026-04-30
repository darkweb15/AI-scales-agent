"""Auto Mail Sending Agent package."""

from .agent import AutoMailAgent, EmailResult
from .email_provider import EmailProvider, EmailSendResult, StubEmailProvider
from .llm_service import LLMService, StubLLMService

__all__ = [
    "AutoMailAgent",
    "EmailResult",
    "EmailProvider",
    "EmailSendResult",
    "StubEmailProvider",
    "LLMService",
    "StubLLMService",
]
