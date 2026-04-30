"""Telephony API interface and stub implementation.

In production this would be backed by Twilio, Bland AI, or Vapi.
The stub is used for testing and local development.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CallSession:
    """Represents an active or completed call session."""

    call_id: str
    # Possible statuses: 'answered', 'no_answer', 'busy', 'voicemail', 'failed'
    status: str
    duration_seconds: Optional[int] = None


class TelephonyAPI:
    """Abstract interface for telephony operations."""

    def initiate_call(self, phone: str) -> CallSession:
        """Initiate an outbound call to *phone*.

        Returns a CallSession whose status reflects the call outcome.
        Raises an exception on API failure.
        """
        raise NotImplementedError

    def leave_voicemail(self, call_id: str, script: str) -> None:
        """Leave a pre-recorded or TTS voicemail on the given call session."""
        raise NotImplementedError

    def get_transcript(self, call_id: str) -> str:
        """Return the raw transcript text for a completed call."""
        raise NotImplementedError


class StubTelephonyAPI(TelephonyAPI):
    """In-memory stub for local development and unit tests.

    Behaviour is controlled by the ``responses`` dict keyed on phone number.
    If a phone number is not in the dict, the call is treated as answered.
    """

    def __init__(self, responses: Optional[dict] = None) -> None:
        # responses: {phone: status_string}
        self._responses: dict = responses or {}
        self._voicemails: list = []
        self._transcripts: dict = {}

    def initiate_call(self, phone: str) -> CallSession:
        status = self._responses.get(phone, "answered")
        return CallSession(call_id=f"call_{phone}", status=status)

    def leave_voicemail(self, call_id: str, script: str) -> None:
        self._voicemails.append({"call_id": call_id, "script": script})

    def get_transcript(self, call_id: str) -> str:
        return self._transcripts.get(call_id, "")
