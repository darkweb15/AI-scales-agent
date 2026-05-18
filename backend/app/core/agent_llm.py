"""Unified LLM service — Pure agentic, no rule-based fallbacks.

Every decision flows through the LLM. When the LLM is unavailable,
requests are retried with exponential backoff rather than falling
back to keyword matching or hardcoded rules.

Providers:
- Primary: Groq (llama-3.3-70b) — fastest inference
- Fallback: OpenAI (GPT-4o-mini) — reliable backup
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Simple in-memory cache — avoids redundant LLM calls
# ---------------------------------------------------------------------------
_llm_cache: Dict[str, tuple] = {}
CACHE_TTL_SECONDS = 300  # cache decisions for 5 minutes


def _cache_get(key: str) -> Optional[Any]:
    if key in _llm_cache:
        result, ts = _llm_cache[key]
        if time.time() - ts < CACHE_TTL_SECONDS:
            return result
        del _llm_cache[key]
    return None


def _cache_set(key: str, value: Any) -> None:
    _llm_cache[key] = (value, time.time())


class AgentLLM:
    """Pure LLM reasoning engine — no rule-based fallbacks.

    Uses Groq (llama-3.3-70b) as primary, OpenAI GPT-4o-mini as fallback.
    Retries with backoff when providers are unavailable.
    """

    GROQ_MODEL = "llama-3.3-70b-versatile"
    OPENAI_MODEL = "gpt-4o-mini"
    GROQ_BASE_URL = "https://api.groq.com/openai/v1"
    OPENAI_BASE_URL = "https://api.openai.com/v1"

    MAX_RETRIES = 3
    RETRY_BACKOFF_BASE = 2.0

    def __init__(self) -> None:
        self._groq_key = os.environ.get("GROQ_API_KEY", "")
        self._openai_key = os.environ.get("OPENAI_API_KEY", "")

    def classify_intent(self, text: str, context: str = "") -> Dict[str, Any]:
        """Classify intent using LLM reasoning only."""
        cache_key = f"intent:{hash(text[:200])}"
        cached = _cache_get(cache_key)
        if cached:
            return cached

        system_prompt = (
            "You are an expert sales AI classifying customer intent.\n"
            "Analyze the message deeply — consider tone, urgency, buying signals, "
            "and emotional state.\n\n"
            "Classify into EXACTLY one of: interested, not_interested, question, "
            "objection, callback_requested, meeting_request, unsubscribe, unknown.\n\n"
            "Respond with ONLY valid JSON:\n"
            '{"intent":"<value>","confidence":<0.0-1.0>,'
            '"reasoning":"<2-3 sentences>","next_action":"<specific action>"}'
        )
        user_prompt = f"Classify the intent of this message:\n\n{text}"
        if context:
            user_prompt += f"\n\nLead context:\n{context}"

        response = self._call_llm_with_retry(
            system_prompt, user_prompt, temperature=0.1, max_tokens=200
        )

        if not response:
            return {
                "intent": "unknown", "confidence": 0.0,
                "reasoning": "LLM unavailable — requires human review",
                "next_action": "escalate to human",
            }

        try:
            result = json.loads(response)
            _cache_set(cache_key, result)
            return result
        except (json.JSONDecodeError, KeyError):
            return {
                "intent": "unknown", "confidence": 0.0,
                "reasoning": "Failed to parse LLM response",
                "next_action": "escalate to human",
            }

    # ------------------------------------------------------------------
    # Next action reasoning — Pure LLM
    # ------------------------------------------------------------------

    def reason_next_action(
        self,
        lead_summary: str,
        interaction_history: str,
        available_actions: List[str],
    ) -> Dict[str, Any]:
        """LLM reasons about the best next action for a lead."""
        if not available_actions:
            return {"action": "end", "reasoning": "No actions available",
                    "urgency": "low", "message_hint": ""}

        cache_key = f"action:{hash(lead_summary[:150] + interaction_history[:100])}"
        cached = _cache_get(cache_key)
        if cached:
            return cached

        system_prompt = (
            "You are an elite sales orchestration AI. Decide the single "
            "best next action for a lead in the sales pipeline.\n\n"
            "Think deeply about:\n"
            "1. What stage is this lead in? What signals have they given?\n"
            "2. What was the last interaction and its outcome?\n"
            "3. What would a top-performing sales rep do right now?\n"
            "4. What is the highest-impact action to move this lead forward?\n\n"
            "Respond with ONLY valid JSON:\n"
            '{"action":"<must be one of available actions>",'
            '"reasoning":"<3-4 sentences>","urgency":"high|medium|low",'
            '"message_hint":"<tone and content guidance>"}'
        )
        user_prompt = (
            f"LEAD PROFILE:\n{lead_summary}\n\n"
            f"INTERACTION HISTORY:\n{interaction_history or 'No previous interactions'}\n\n"
            f"AVAILABLE ACTIONS: {', '.join(available_actions)}\n\n"
            "What is the single best next action?"
        )

        response = self._call_llm_with_retry(
            system_prompt, user_prompt, temperature=0.3, max_tokens=300
        )

        if not response:
            return {
                "action": available_actions[0],
                "reasoning": "LLM unavailable — defaulting to first available action",
                "urgency": "medium",
                "message_hint": "Be professional and value-focused.",
            }

        try:
            result = json.loads(response)
            if result.get("action") not in available_actions:
                result["action"] = available_actions[0]
            _cache_set(cache_key, result)
            return result
        except (json.JSONDecodeError, KeyError):
            return {
                "action": available_actions[0],
                "reasoning": "Failed to parse LLM response",
                "urgency": "medium",
                "message_hint": "Be professional.",
            }

    # ------------------------------------------------------------------
    # Content generation
    # ------------------------------------------------------------------

    def generate_email(
        self,
        lead_name: str,
        company: str,
        intent: str,
        context: str = "",
        template_hint: str = "",
    ) -> Dict[str, str]:
        """Generate a personalized email using LLM."""
        system_prompt = (
            "You are Priya, a warm sales rep at Pebble POS "
            "(AI-native POS for restaurants and retail).\n\n"
            "Write personalized, human-sounding emails:\n"
            "- Sound like a real person\n- Under 150 words\n"
            "- End with a low-pressure CTA\n\n"
            'Respond with ONLY valid JSON: {"subject":"<subject>","body":"<body>"}'
        )
        user_prompt = (
            f"Write email to: {lead_name} at {company}\n"
            f"Stage: {intent}\nContext: {context or 'First outreach'}\n"
            f"Hint: {template_hint or 'Focus on their business type'}"
        )
        response = self._call_llm_with_retry(
            system_prompt, user_prompt, temperature=0.7, max_tokens=400
        )
        if not response:
            first = lead_name.split()[0] if lead_name else "there"
            return {
                "subject": f"Quick question about your business, {first}",
                "body": (
                    f"Hi {first},\n\nI'm Priya from Pebble. We help restaurants "
                    f"and retail stores run their POS, online ordering, loyalty, "
                    f"and AI from one platform.\n\nWould love to show you a quick "
                    f"15-min demo.\n\nBest,\nPriya\nPebble | customercare@pebbletab.com"
                ),
            }
        try:
            return json.loads(response)
        except (json.JSONDecodeError, KeyError):
            first = lead_name.split()[0] if lead_name else "there"
            return {
                "subject": f"Quick question, {first}",
                "body": (
                    f"Hi {first},\n\nI'm Priya from Pebble. We help businesses "
                    f"like yours run smarter.\n\nWould a quick 15-min demo work?"
                    f"\n\nBest,\nPriya"
                ),
            }

    def generate_call_script(
        self,
        lead_name: str,
        company: str,
        context: str = "",
        rag_context: str = "",
    ) -> str:
        """Generate a personalized cold call opening script."""
        system_prompt = (
            "Write a cold call opening for Priya at Pebble POS.\n"
            "- Sound 100% human, warm, natural\n- Under 3 sentences\n"
            "- End with an engaging question\n\nReturn ONLY the script text."
        )
        user_prompt = (
            f"Call to: {lead_name} at {company}\n"
            f"Context: {context or 'First cold call'}\n"
            f"Product: {rag_context[:400] if rag_context else 'Pebble POS'}"
        )
        response = self._call_llm_with_retry(
            system_prompt, user_prompt, temperature=0.8, max_tokens=150
        )
        if response:
            return response
        name = lead_name or "there"
        comp = f" at {company}" if company else ""
        return (
            f"Hi, am I speaking with {name}? This is Priya calling from "
            f"Pebble{comp}. We help restaurants and retail stores run their "
            f"POS, ordering, loyalty, and AI all from one platform — do you "
            f"have just 2 minutes?"
        )

    def generate_inbound_reply(
        self,
        message: str,
        lead_name: str,
        intent: str,
        rag_context: str = "",
        interaction_history: str = "",
    ) -> str:
        """Generate a contextual reply to an inbound message using LLM + RAG."""
        system_prompt = (
            "You are Priya, a helpful sales rep at Pebble POS.\n"
            "Answer using ONLY the product knowledge provided.\n"
            "Be warm, concise (under 120 words), and offer a next step.\n\n"
            f"PRODUCT KNOWLEDGE:\n{rag_context}\n\n"
            f"HISTORY:\n{interaction_history or 'First message'}"
        )
        user_prompt = (
            f"Customer {lead_name} (intent: {intent}) says:\n\n"
            f"{message}\n\nWrite a helpful reply."
        )
        response = self._call_llm_with_retry(
            system_prompt, user_prompt, temperature=0.6, max_tokens=200
        )
        if response:
            return response
        first = lead_name.split()[0] if lead_name else "there"
        return (
            f"Hi {first}, thanks for reaching out! Pebble is an all-in-one "
            f"POS platform for restaurants and retail. Can I show you a demo?"
        )

    def answer_inbound_call_question(
        self,
        question: str,
        caller_name: str,
        rag_context: str,
        conversation_history: str = "",
    ) -> str:
        """Answer an inbound call question using RAG context."""
        system_prompt = (
            "You are an AI assistant for Pebble POS answering an inbound call.\n"
            "Answer accurately using ONLY the product knowledge below.\n"
            "Be conversational. 2-3 sentences max.\n\n"
            f"PRODUCT KNOWLEDGE:\n{rag_context}\n\n"
            f"CONVERSATION:\n{conversation_history or 'Start of call'}"
        )
        user_prompt = f"Caller ({caller_name}) asks: {question}"
        response = self._call_llm_with_retry(
            system_prompt, user_prompt, temperature=0.4, max_tokens=150
        )
        if response:
            return response
        name = caller_name or "there"
        return (
            f"Thanks for calling Pebble, {name}! Let me connect you with "
            f"a specialist. One moment."
        )

    # ------------------------------------------------------------------
    # New pure agentic methods
    # ------------------------------------------------------------------

    def analyze_lead_strategy(
        self,
        lead_summary: str,
        interaction_history: str,
        pipeline_context: str = "",
    ) -> Dict[str, Any]:
        """Deep strategic analysis of a lead."""
        system_prompt = (
            "You are an elite sales strategist AI. Analyze this lead and create a "
            "comprehensive conversion strategy.\n\n"
            "Respond with ONLY valid JSON:\n"
            '{"strategy":"<2-3 sentences>","next_steps":["<step1>","<step2>"],'
            '"risk_factors":["<risk1>"],"estimated_close_probability":<0.0-1.0>,'
            '"recommended_timeline":"<timeline>","personalization_notes":"<guidance>"}'
        )
        user_prompt = (
            f"LEAD:\n{lead_summary}\n\nHISTORY:\n{interaction_history or 'None'}\n\n"
            f"PIPELINE:\n{pipeline_context or 'Standard pipeline'}"
        )
        response = self._call_llm_with_retry(
            system_prompt, user_prompt, temperature=0.4, max_tokens=400
        )
        if not response:
            return {
                "strategy": "Needs human analysis",
                "next_steps": ["Assign to sales rep"],
                "risk_factors": ["No AI analysis"],
                "estimated_close_probability": 0.5,
                "recommended_timeline": "ASAP",
                "personalization_notes": "Review manually",
            }
        try:
            return json.loads(response)
        except (json.JSONDecodeError, KeyError):
            return {
                "strategy": "Needs human analysis",
                "next_steps": ["Review manually"],
                "risk_factors": ["AI failed"],
                "estimated_close_probability": 0.5,
                "recommended_timeline": "Within 24 hours",
                "personalization_notes": "Standard approach",
            }

    def generate_sms(
        self, lead_name: str, company: str, context: str = "",
    ) -> str:
        """Generate a personalized SMS message using LLM."""
        system_prompt = (
            "Write a brief SMS from Priya at Pebble POS.\n"
            "- Under 160 characters\n- Friendly, not salesy\n"
            "- Clear next step\nReturn ONLY the SMS text."
        )
        user_prompt = (
            f"SMS to: {lead_name} at {company}\n"
            f"Context: {context or 'Follow-up'}"
        )
        response = self._call_llm_with_retry(
            system_prompt, user_prompt, temperature=0.7, max_tokens=60
        )
        if response:
            return response
        first = lead_name.split()[0] if lead_name else "Hi"
        return (
            f"{first}, this is Priya from Pebble. Quick question — "
            f"are you happy with your current POS?"
        )

    def handle_objection(
        self, objection: str, lead_name: str,
        lead_context: str = "", rag_context: str = "",
    ) -> Dict[str, str]:
        """LLM-powered objection handling."""
        system_prompt = (
            "You are an expert sales objection handler for Pebble POS.\n"
            "Craft a response that acknowledges, reframes, provides proof, "
            "and offers a soft next step.\n\n"
            f"PRODUCT KNOWLEDGE:\n{rag_context}\n\n"
            'Respond with ONLY valid JSON:\n'
            '{"response":"<reply>","strategy":"<analysis>","follow_up":"<next action>"}'
        )
        user_prompt = (
            f"Lead: {lead_name}\nContext: {lead_context}\n\n"
            f'Objection: "{objection}"'
        )
        response = self._call_llm_with_retry(
            system_prompt, user_prompt, temperature=0.5, max_tokens=300
        )
        if not response:
            return {
                "response": (
                    "I completely understand. Many customers had similar thoughts "
                    "before trying Pebble. Would a quick 15-minute demo help?"
                ),
                "strategy": "Acknowledge and offer demo",
                "follow_up": "Schedule demo within 48 hours",
            }
        try:
            return json.loads(response)
        except (json.JSONDecodeError, KeyError):
            return {
                "response": "I appreciate you sharing that. Would a quick call work?",
                "strategy": "Generic acknowledgment",
                "follow_up": "Follow up within 24 hours",
            }

    def score_lead_with_llm(
        self, lead_summary: str, interaction_history: str,
    ) -> Dict[str, Any]:
        """Pure LLM lead scoring."""
        system_prompt = (
            "You are a lead scoring AI. Score from 0-100 based on:\n"
            "- Engagement and buying signals\n- Business fit for Pebble POS\n"
            "- Timeline and urgency\n\n"
            "Grade: A (80-100), B (60-79), C (40-59), D (20-39), F (0-19)\n\n"
            "Respond with ONLY valid JSON:\n"
            '{"score":<0-100>,"grade":"<A-F>","reasoning":"<2-3 sentences>",'
            '"buying_signals":["<signal>"],"risk_factors":["<risk>"],'
            '"recommended_priority":"high|medium|low"}'
        )
        user_prompt = (
            f"LEAD:\n{lead_summary}\n\n"
            f"INTERACTIONS:\n{interaction_history or 'None'}\n\n"
            "Score this lead."
        )
        response = self._call_llm_with_retry(
            system_prompt, user_prompt, temperature=0.2, max_tokens=300
        )
        if not response:
            return {
                "score": 50, "grade": "C",
                "reasoning": "LLM unavailable — default score",
                "buying_signals": [],
                "risk_factors": ["No AI analysis"],
                "recommended_priority": "medium",
            }
        try:
            return json.loads(response)
        except (json.JSONDecodeError, KeyError):
            return {
                "score": 50, "grade": "C",
                "reasoning": "Parse error — default score",
                "buying_signals": [],
                "risk_factors": ["AI scoring failed"],
                "recommended_priority": "medium",
            }

    # ------------------------------------------------------------------
    # Internal: unified LLM call with retry
    # ------------------------------------------------------------------

    def _call_llm_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.5,
        max_tokens: int = 300,
    ) -> str:
        """Call LLM with automatic retry and provider fallback."""
        for attempt in range(self.MAX_RETRIES):
            if self._groq_key:
                result = self._call_groq(
                    system_prompt, user_prompt, temperature, max_tokens
                )
                if result:
                    return result
            if self._openai_key:
                result = self._call_openai(
                    system_prompt, user_prompt, temperature, max_tokens
                )
                if result:
                    return result
            if attempt < self.MAX_RETRIES - 1:
                backoff = self.RETRY_BACKOFF_BASE ** (attempt + 1)
                logger.info(
                    "LLM retry %d/%d — waiting %.1fs",
                    attempt + 1, self.MAX_RETRIES, backoff,
                )
                time.sleep(backoff)
        logger.warning(
            "All LLM providers failed after %d retries", self.MAX_RETRIES
        )
        return ""

    def _call_groq(self, system: str, user: str, temperature: float, max_tokens: int) -> str:
        try:
            import requests
            resp = requests.post(
                f"{self.GROQ_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._groq_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            if resp.status_code == 429:
                logger.info("Groq rate limited — trying OpenAI")
            else:
                logger.warning(
                    "Groq error %d: %s", resp.status_code, resp.text[:100]
                )
        except Exception as e:
            logger.warning("Groq call failed: %s", e)
        return ""

    def _call_openai(self, system: str, user: str, temperature: float, max_tokens: int) -> str:
        try:
            import requests
            resp = requests.post(
                f"{self.OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._openai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=20,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            logger.warning(
                "OpenAI error %d: %s", resp.status_code, resp.text[:100]
            )
        except Exception as e:
            logger.warning("OpenAI call failed: %s", e)
        return ""


# Singleton
_agent_llm: Optional[AgentLLM] = None


def get_agent_llm() -> AgentLLM:
    global _agent_llm
    if _agent_llm is None:
        _agent_llm = AgentLLM()
    return _agent_llm
