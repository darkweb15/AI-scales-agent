"""Twilio telephony integration for outbound calls."""
from __future__ import annotations

import logging
import os
import uuid
from typing import Optional

import requests

from .telephony import CallSession, TelephonyAPI

logger = logging.getLogger(__name__)


class TwilioTelephonyAPI(TelephonyAPI):
    """Twilio REST API integration.

    Credentials from .env:
        TWILIO_ACCOUNT_SID
        TWILIO_AUTH_TOKEN
        TWILIO_FROM_NUMBER
    """

    def __init__(self) -> None:
        self._sid   = os.environ.get("TWILIO_ACCOUNT_SID", "")
        self._token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        self._from  = os.environ.get("TWILIO_FROM_NUMBER", "+19785435923")

    @property
    def _base_url(self) -> str:
        return f"https://api.twilio.com/2010-04-01/Accounts/{self._sid}/Calls.json"

    def initiate_call(self, phone: str) -> CallSession:
        logger.info("Twilio: calling %s from %s", phone, self._from)

        # Polly.Aditi — Indian English female voice (sounds natural, free with Twilio)
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '<Say voice="Polly.Aditi" language="en-IN">'
            'Hi, am I speaking with the owner or manager? '
            'This is Priya calling from Pebble. '
            'We help restaurants and retail stores run their POS, online ordering, loyalty, and AI all from one platform. '
            'Do you have just 2 minutes?'
            '</Say>'
            '<Gather input="speech" speechTimeout="3" timeout="10" action="/api/voice/respond" method="POST"/>'
            '</Response>'
        )

        resp = requests.post(
            self._base_url,
            auth=(self._sid, self._token),
            data={"To": phone, "From": self._from, "Twiml": twiml},
            timeout=30,
        )

        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Twilio error {resp.status_code}: {resp.text}")

        data = resp.json()
        call_sid = data.get("sid", str(uuid.uuid4()))
        status_map = {"queued": "answered", "ringing": "answered",
                      "in-progress": "answered", "no-answer": "no_answer",
                      "busy": "busy", "failed": "failed"}
        status = status_map.get(data.get("status", "queued"), "answered")
        logger.info("Twilio call: sid=%s status=%s", call_sid, status)
        return CallSession(call_id=call_sid, status=status)

    def leave_voicemail(self, call_id: str, script: str) -> None:
        logger.info("Twilio voicemail for %s", call_id)

    def get_transcript(self, call_id: str) -> str:
        return f"[Twilio call {call_id}]"
