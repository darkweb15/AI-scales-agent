"""Vapi.ai telephony — uses pre-configured Priya assistant.

The Priya assistant (ID: 943a46e5-07a7-4387-b7aa-139e96d83acf) is configured
directly in Vapi dashboard with:
- Voice: Jessica (ElevenLabs) — warm, natural American female
- Model: GPT-4o-mini — natural conversation
- Backchanneling, interruption handling, response delay all set
"""
from __future__ import annotations

import logging
import os
import uuid

import requests

from .telephony import CallSession, TelephonyAPI

logger = logging.getLogger(__name__)

# Pre-configured Priya assistant in Vapi — updated via API, not inline
PRIYA_ASSISTANT_ID = "943a46e5-07a7-4387-b7aa-139e96d83acf"


class VapiTelephonyAPI(TelephonyAPI):
    """Vapi.ai — best-in-class human voice AI calling."""

    BASE_URL = "https://api.vapi.ai"

    def __init__(self) -> None:
        self._api_key = os.environ.get("VAPI_API_KEY", "")
        self._phone_number_id = os.environ.get("VAPI_PHONE_NUMBER_ID", "")

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def get_phone_numbers(self) -> list:
        resp = requests.get(f"{self.BASE_URL}/phone-number", headers=self._headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return []

    def initiate_call(self, phone: str, lead_name: str = "", company: str = "") -> CallSession:
        """Initiate a call using the pre-configured Priya assistant."""
        logger.info("Vapi: calling %s (lead=%s, company=%s)", phone, lead_name, company)

        name = lead_name or "there"
        comp = f" at {company}" if company else ""

        phone_number_id = self._phone_number_id
        if not phone_number_id:
            numbers = self.get_phone_numbers()
            if numbers:
                phone_number_id = numbers[0].get("id", "")
                logger.info("Vapi: auto-selected phone number id=%s", phone_number_id)

        payload = {
            "phoneNumberId": phone_number_id,
            "assistantId": PRIYA_ASSISTANT_ID,
            # Override just the first message to personalize with lead name/company
            "assistantOverrides": {
                "firstMessage": (
                    f"Hey, good morning! This is Priya calling from Pebble{comp}. "
                    f"We help restaurants and retail stores with their POS, ordering, and AI — all in one platform. "
                    f"Am I speaking with the owner or manager? Do you have just 2 minutes?"
                ),
            },
            "customer": {
                "number": phone,
                "name": lead_name or "Lead",
            },
            "metadata": {
                "lead_name": lead_name,
                "company": company,
                "source": "salesai_platform",
            },
        }

        if not phone_number_id:
            del payload["phoneNumberId"]

        resp = requests.post(
            f"{self.BASE_URL}/call/phone",
            headers=self._headers,
            json=payload,
            timeout=30,
        )

        if resp.status_code not in (200, 201):
            logger.error("Vapi call failed: %s %s", resp.status_code, resp.text)
            raise RuntimeError(f"Vapi error {resp.status_code}: {resp.text}")

        data = resp.json()
        call_id = data.get("id", str(uuid.uuid4()))
        logger.info("Vapi call initiated: id=%s", call_id)
        return CallSession(call_id=call_id, status="answered")

    def get_call_details(self, call_id: str) -> dict:
        resp = requests.get(
            f"{self.BASE_URL}/call/{call_id}",
            headers=self._headers,
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
        return {}

    def leave_voicemail(self, call_id: str, script: str) -> None:
        logger.info("Vapi handles voicemail automatically for call %s", call_id)

    def get_transcript(self, call_id: str) -> str:
        data = self.get_call_details(call_id)
        transcript = data.get("transcript", "")
        if transcript:
            return transcript
        messages = data.get("messages", [])
        if messages:
            lines = [f"{m.get('role', '')}: {m.get('message', '')}" for m in messages]
            return "\n".join(lines)
        return f"[Vapi call {call_id} — transcript pending]"
