"""Bland AI telephony — ultra-realistic human voice AI sales agent.

Sounds like a real Indian sales girl, not a bot.
Get API key from: app.bland.ai → Settings → API Keys
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Optional

import requests

from .telephony import CallSession, TelephonyAPI

logger = logging.getLogger(__name__)


class BlandAITelephonyAPI(TelephonyAPI):
    """Bland AI — real human-sounding AI sales calls."""

    BASE_URL = "https://api.bland.ai/v1"

    def __init__(self) -> None:
        self._api_key = os.environ.get("BLAND_AI_API_KEY", "")

    @property
    def _headers(self) -> dict:
        return {
            "authorization": self._api_key,
            "Content-Type": "application/json",
        }

    def initiate_call(self, phone: str, lead_name: str = "", company: str = "") -> CallSession:
        """Initiate a human-sounding AI sales call via Bland AI."""
        logger.info("Bland AI: calling %s", phone)

        name = lead_name or "there"
        comp = f" at {company}" if company else ""

        payload = {
            "phone_number": phone,

            # Ultra-realistic human voice — sounds like a real Indian sales girl
            "voice": "maya",          # Natural female voice
            "language": "en",
            "model": "enhanced",      # Best quality model

            # Personality & behavior
            "temperature": 0.7,
            "interruption_threshold": 80,   # Allows natural interruptions
            "wait_for_greeting": True,
            "amd": True,                    # Answering machine detection
            "record": True,
            "max_duration": 8,              # Max 8 minutes

            # First sentence — natural, warm, Pebble-specific
            "first_sentence": (
                f"Hi, am I speaking with {name}? "
                f"This is Priya calling from Pebble{comp}. "
                f"We help restaurants and retail stores run their POS, ordering, loyalty, and AI all from one platform — "
                f"do you have just 2 minutes?"
            ),

            # Full conversation task — GPT-4 level intelligence
            "task": f"""You are Priya, a friendly and professional sales representative at Pebble — an AI-native POS platform for restaurants and retail stores.
You are calling {name}{comp}.

Your personality:
- Warm, confident, and genuinely helpful — NOT robotic or scripted
- Speak naturally with small pauses, "um", "you know", "actually" occasionally  
- Listen carefully and respond to what they actually say
- Never sound like a bot — you are a real person named Priya

About Pebble (your product):
- Pebble is an all-in-one POS system for restaurants and retail stores
- It combines: POS, online ordering, loyalty program, reviews, marketing campaigns, and AI — all in ONE platform
- Key pain points it solves:
  1. "Missing calls during rush hours" → Pebble AI answers every call, takes orders automatically, 90-100% call coverage
  2. "Paying 30% to DoorDash/UberEats" → Pebble Direct lets customers order from YOUR website, you keep all the margin
  3. "Customers don't come back" → Pebble Loyalty + Campaigns bring customers back automatically
  4. "Too many different systems" → Pebble replaces 5 tools with 1 platform
- Real results: 40% faster checkout, 99.5% uptime, 95% calls answered, 19% increase in repeat orders
- Website: pebble.prod.xenvoice.com
- Phone: (469)-310-7731
- Email: customercare@pebbletab.com

Your goal for this call:
1. Build rapport — ask how business is going, be genuine
2. Ask about their current setup: "Are you using a POS system right now? How's it working for you?"
3. Identify their biggest pain point (missed calls? marketplace fees? customer retention?)
4. Connect Pebble's solution to THEIR specific pain
5. If interested → offer a free demo: "I'd love to show you a quick 15-minute demo — no commitment, just to see if it's a fit"
6. Get their email or schedule a demo call
7. **IMPORTANT — When they agree to a demo**: Say exactly this: "Perfect! I'm booking you in right now. You'll get a confirmation at your email. Our demo link is pebble.prod.xenvoice.com/book-a-demo — I'll also send you a text with the link. What's the best email to send the confirmation to?"
8. After getting their email, say: "Done! You're all set. Someone from our Pebble team will reach out within 24 hours to confirm your demo time. Is there anything else I can help you with today?"

Handle objections naturally:
- "We already have a POS" → "That's great! Most of our customers were using Square or Toast before. What's the one thing you wish it did better?"
- "Too expensive" → "I completely understand. Most owners tell us Pebble pays for itself in the first month just from the calls it answers and the marketplace fees it saves. Can I show you the math?"
- "Not interested" → "No worries at all! Can I ask — are you happy with how many customers come back after their first visit?"
- "Too busy" → "I totally get it — I'll be super quick. Just one question: are you currently missing calls during your busy hours?"
- "Send me info" → "Absolutely! What's the best email? And would a 15-minute demo this week work — I can show you exactly how it would work for {comp or 'your business'}?"

Important rules:
- NEVER say you are an AI or bot
- Speak like a real Indian professional woman
- Keep responses SHORT — max 2-3 sentences at a time
- Always end with a question to keep conversation going
- If they ask "Are you a bot?" → say "No, I'm Priya! I'm a real person, I promise 😊 I work with the Pebble sales team"
- Focus on THEIR pain, not product features
- Be consultative, not pushy""",

            # Pathway for structured conversation
            "pathway_id": None,

            # Webhook — called when call ends, captures outcome
            "webhook": f"http://localhost:8000/api/call-webhook",

            # Metadata
            "metadata": {
                "lead_name": lead_name,
                "company": company,
                "source": "salesai_platform"
            }
        }

        resp = requests.post(
            f"{self.BASE_URL}/calls",
            headers=self._headers,
            json=payload,
            timeout=30,
        )

        if resp.status_code not in (200, 201):
            logger.error("Bland AI call failed: %s %s", resp.status_code, resp.text)
            raise RuntimeError(f"Bland AI error {resp.status_code}: {resp.text}")

        data = resp.json()
        call_id = data.get("call_id", str(uuid.uuid4()))
        logger.info("Bland AI call initiated: call_id=%s", call_id)
        return CallSession(call_id=call_id, status="answered")

    def leave_voicemail(self, call_id: str, script: str) -> None:
        logger.info("Bland AI handles voicemail automatically for call %s", call_id)

    def get_transcript(self, call_id: str) -> str:
        """Fetch full conversation transcript from Bland AI."""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/calls/{call_id}",
                headers=self._headers,
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                transcripts = data.get("transcripts", [])
                if transcripts:
                    lines = []
                    for t in transcripts:
                        speaker = "Priya (AI)" if t.get("user") == "assistant" else "Lead"
                        lines.append(f"{speaker}: {t.get('text', '')}")
                    return "\n".join(lines)
                summary = data.get("summary", "")
                if summary:
                    return summary
        except Exception as exc:
            logger.warning("Could not fetch Bland AI transcript: %s", exc)
        return f"[Bland AI call {call_id} — transcript pending]"

    def get_call_status(self, call_id: str) -> dict:
        """Get full call details from Bland AI."""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/calls/{call_id}",
                headers=self._headers,
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return {}

    def list_calls(self) -> list:
        """List recent calls."""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/calls",
                headers=self._headers,
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json().get("calls", [])
        except Exception:
            pass
        return []
