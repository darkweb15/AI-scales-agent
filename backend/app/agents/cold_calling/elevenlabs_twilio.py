"""Twilio + ElevenLabs AI calling system.

Architecture:
1. Twilio calls the lead
2. Lead answers → Twilio webhook hits our server
3. Groq generates AI response text
4. ElevenLabs converts text to ultra-realistic voice audio
5. Twilio plays audio to lead via TwiML
6. Repeat until call ends

This creates a real-time AI conversation that sounds 100% human.
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Optional

import requests

from .telephony import CallSession, TelephonyAPI

logger = logging.getLogger(__name__)

# ElevenLabs voice IDs — choose the best one
VOICE_IDS = {
    "rachel":  "21m00Tcm4TlvDq8ikWAM",  # Professional American female
    "bella":   "EXAVITQu4vr4xnSDxMaL",  # Warm, friendly female
    "elli":    "MF3mGyEYCl7XYWbV9V6O",  # Energetic female
    "domi":    "AZnzlk1XvdvUeBnXmlld",  # Strong female
    "josh":    "TxGEqnHWrfWFTfGW9XjX",  # Deep male
}


class ElevenLabsTwilioAgent(TelephonyAPI):
    """Real AI calling using Twilio (delivery) + ElevenLabs (voice) + Groq (brain)."""

    def __init__(self) -> None:
        # Twilio
        self._twilio_sid   = os.environ.get("TWILIO_ACCOUNT_SID", "")
        self._twilio_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        self._twilio_from  = os.environ.get("TWILIO_FROM_NUMBER", "+19785435923")

        # ElevenLabs
        self._el_key     = os.environ.get("ELEVENLABS_API_KEY", "")
        self._el_voice   = os.environ.get("ELEVENLABS_VOICE_ID", VOICE_IDS["rachel"])

        # Server URL for Twilio webhooks (needs to be public — use ngrok for local dev)
        self._server_url = os.environ.get("SERVER_URL", "http://localhost:8001")

    def text_to_speech(self, text: str) -> bytes:
        """Convert text to ultra-realistic speech using ElevenLabs."""
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self._el_voice}"
        headers = {
            "xi-api-key": self._el_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2",  # Fastest model
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8,
                "style": 0.3,
                "use_speaker_boost": True,
            },
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            return resp.content
        raise RuntimeError(f"ElevenLabs error {resp.status_code}: {resp.text}")

    def get_available_voices(self) -> list:
        """List available ElevenLabs voices."""
        resp = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": self._el_key},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("voices", [])
        return []

    def initiate_call(self, phone: str) -> CallSession:
        """Initiate outbound call via Twilio with ElevenLabs voice webhook."""
        logger.info("ElevenLabs+Twilio: calling %s", phone)

        # The webhook URL that Twilio will call when the lead answers
        # This serves TwiML with ElevenLabs audio
        webhook_url = f"{self._server_url}/api/voice/answer"

        resp = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{self._twilio_sid}/Calls.json",
            auth=(self._twilio_sid, self._twilio_token),
            data={
                "To":   phone,
                "From": self._twilio_from,
                "Url":  webhook_url,
                "StatusCallback": f"{self._server_url}/api/voice/status",
                "StatusCallbackMethod": "POST",
            },
            timeout=30,
        )

        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Twilio error {resp.status_code}: {resp.text}")

        data = resp.json()
        call_sid = data.get("sid", str(uuid.uuid4()))
        logger.info("Call initiated: sid=%s", call_sid)
        return CallSession(call_id=call_sid, status="answered")

    def leave_voicemail(self, call_id: str, script: str) -> None:
        logger.info("Voicemail for call %s", call_id)

    def get_transcript(self, call_id: str) -> str:
        return f"[Call {call_id} transcript]"
