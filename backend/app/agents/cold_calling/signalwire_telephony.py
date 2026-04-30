"""SignalWire telephony integration — uses REST API directly (no SDK conflicts)."""
from __future__ import annotations

import logging
import os
import uuid
from typing import Optional

import requests

from .telephony import CallSession, TelephonyAPI

logger = logging.getLogger(__name__)


class SignalWireTelephonyAPI(TelephonyAPI):
    """Real SignalWire telephony via REST API.

    Credentials from .env:
        SIGNALWIRE_PROJECT_ID  = 39177ad6-fccc-4cfd-8c90-504f64f41776
        SIGNALWIRE_TOKEN       = PT9ee2743d248428ad8c23500e459a78c008032b6df84541c3
        SIGNALWIRE_SPACE_URL   = ajr-info-systems.signalwire.com
        SIGNALWIRE_FROM_NUMBER = +12014092739
    """

    def __init__(self) -> None:
        self._project_id  = os.environ.get("SIGNALWIRE_PROJECT_ID", "")
        self._token       = os.environ.get("SIGNALWIRE_TOKEN", "")
        self._space_url   = os.environ.get("SIGNALWIRE_SPACE_URL", "")
        self._from_number = os.environ.get("SIGNALWIRE_FROM_NUMBER", "+12014092739")

    @property
    def _base_url(self) -> str:
        return f"https://{self._space_url}/api/laml/2010-04-01/Accounts/{self._project_id}"

    @property
    def _auth(self):
        return (self._project_id, self._token)

    def initiate_call(self, phone: str) -> CallSession:
        """Initiate outbound call via SignalWire REST API."""
        logger.info("SignalWire: calling %s from %s", phone, self._from_number)

        # Polly.Aditi — Indian English female voice (natural, human-sounding)
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Response>'
            '<Say voice="Polly.Aditi" language="en-IN">'
            'Hi, am I speaking with the owner or manager? '
            'This is Priya calling from Pebble. '
            'We help restaurants and retail stores run their POS, online ordering, loyalty, and AI all from one platform. '
            'Do you have just 2 minutes?'
            '</Say>'
            '</Response>'
        )

        resp = requests.post(
            f"{self._base_url}/Calls.json",
            auth=self._auth,
            data={
                "To":    phone,
                "From":  self._from_number,
                "Twiml": twiml,
                "StatusCallback": "",
            },
            timeout=30,
        )

        if resp.status_code not in (200, 201):
            logger.error("SignalWire call failed: %s %s", resp.status_code, resp.text)
            raise RuntimeError(f"SignalWire error {resp.status_code}: {resp.text}")

        data = resp.json()
        call_sid = data.get("sid", str(uuid.uuid4()))
        raw_status = data.get("status", "queued")

        status_map = {
            "in-progress": "answered",
            "ringing":     "answered",
            "queued":      "answered",
            "no-answer":   "no_answer",
            "busy":        "busy",
            "failed":      "failed",
            "completed":   "answered",
        }
        status = status_map.get(raw_status, "answered")
        logger.info("SignalWire call initiated: sid=%s status=%s", call_sid, status)
        return CallSession(call_id=call_sid, status=status)

    def leave_voicemail(self, call_id: str, script: str) -> None:
        logger.info("SignalWire: voicemail for call %s", call_id)

    def get_transcript(self, call_id: str) -> str:
        """Fetch recording/transcript from SignalWire."""
        try:
            resp = requests.get(
                f"{self._base_url}/Calls/{call_id}/Recordings.json",
                auth=self._auth,
                timeout=15,
            )
            if resp.status_code == 200:
                recordings = resp.json().get("recordings", [])
                if recordings:
                    return f"Recording URL: {recordings[0].get('uri', '')}"
        except Exception as exc:
            logger.warning("Could not fetch transcript: %s", exc)
        return f"[Call {call_id} — transcript pending]"

    def get_call_status(self, call_id: str) -> str:
        """Check live call status."""
        try:
            resp = requests.get(
                f"{self._base_url}/Calls/{call_id}.json",
                auth=self._auth,
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json().get("status", "unknown")
        except Exception:
            pass
        return "unknown"
