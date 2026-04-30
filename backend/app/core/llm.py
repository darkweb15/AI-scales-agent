"""Groq LLM service — ultra-fast AI responses for sales conversations."""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class GroqLLM:
    """Groq API — fastest LLM inference available.
    
    Uses llama-3.3-70b-versatile for smart, natural sales conversations.
    """

    BASE_URL = "https://api.groq.com/openai/v1"
    MODEL = "llama-3.3-70b-versatile"

    def __init__(self) -> None:
        self._api_key = os.environ.get("GROQ_API_KEY", "")

    def generate_call_script(self, lead_name: str, company: str, context: str = "") -> str:
        """Generate a personalized, human-like Pebble sales call opening."""
        if not self._api_key:
            return self._default_script(lead_name, company)

        try:
            import requests
            resp = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are writing a sales call opening for Priya, a sales rep at Pebble POS. "
                                "Pebble is an AI-native POS for restaurants and retail stores. "
                                "The script must sound 100% human — warm, natural, conversational. "
                                "No robotic language. Keep it under 2 sentences. "
                                "End with a question to engage the prospect."
                            )
                        },
                        {
                            "role": "user",
                            "content": (
                                f"Write a natural opening for a cold call to {lead_name} "
                                f"{'at ' + company if company else ''}. "
                                f"Introduce Pebble — an all-in-one POS that helps restaurants and retail stores "
                                f"with ordering, loyalty, AI call answering, and marketing. "
                                f"Be warm and ask if they have 2 minutes."
                            )
                        }
                    ],
                    "temperature": 0.8,
                    "max_tokens": 100,
                },
                timeout=8,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("Groq LLM failed: %s", exc)

        return self._default_script(lead_name, company)

    def generate_reply(self, message: str, context: str = "") -> str:
        """Generate a smart reply to an inbound message."""
        if not self._api_key:
            return "Thank you for reaching out! Our team will get back to you shortly."

        try:
            import requests
            resp = requests.post(
                f"{self.BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a professional sales representative at SalesAI. "
                                "Reply to customer messages in a warm, helpful, and concise way. "
                                "Never reveal you are an AI. Keep replies under 100 words."
                            )
                        },
                        {
                            "role": "user",
                            "content": f"Customer message: {message}\n\nContext: {context}"
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 150,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("Groq reply failed: %s", exc)

        return "Thank you for your message! I'll get back to you shortly with more details."

    def _default_script(self, lead_name: str, company: str) -> str:
        name = lead_name or "there"
        comp = f" at {company}" if company else ""
        return (
            f"Hi, am I speaking with {name}? "
            f"This is Priya calling from Pebble{comp}. "
            f"We help restaurants and retail stores run their POS, ordering, loyalty, and AI all from one platform — "
            f"do you have just 2 minutes?"
        )
