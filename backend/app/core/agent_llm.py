"""Unified LLM service for all agents — Groq (primary) with smart caching.

Free-tier friendly:
- Caches intent/decision results per lead to avoid redundant calls
- Falls back to weighted rule-based reasoning when rate limited
- Groq free tier: 30 req/min, 14,400 req/day — enough for dev
- After project completion, swap in paid keys for full LLM power
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


# ---------------------------------------------------------------------------
# AgentLLM
# ---------------------------------------------------------------------------

class AgentLLM:
    """Real LLM reasoning engine for all agents.

    Uses Groq (llama-3.3-70b) — fastest free inference available.
    Falls back to weighted rule-based reasoning when rate limited.
    Caches results to minimize API calls during development.
    """

    GROQ_MODEL = "llama-3.3-70b-versatile"
    OPENAI_MODEL = "gpt-4o-mini"
    GROQ_BASE_URL = "https://api.groq.com/openai/v1"
    OPENAI_BASE_URL = "https://api.openai.com/v1"

    def __init__(self) -> None:
        self._groq_key = os.environ.get("GROQ_API_KEY", "")
        self._openai_key = os.environ.get("OPENAI_API_KEY", "")
        self._last_rate_limit_ts: float = 0
        self._rate_limit_backoff: float = 65  # wait 65s after 429

    def _is_rate_limited(self) -> bool:
        if self._last_rate_limit_ts == 0:
            return False
        return (time.time() - self._last_rate_limit_ts) < self._rate_limit_backoff

    # ------------------------------------------------------------------
    # Intent classification — LLM with weighted rule-based fallback
    # ------------------------------------------------------------------

    def classify_intent(self, text: str, context: str = "") -> Dict[str, Any]:
        """Classify intent from any text.

        Uses LLM when available, falls back to weighted rule-based scoring
        when rate limited. Caches results for 5 minutes.

        Returns:
            {
                "intent": "interested|not_interested|question|objection|
                           callback_requested|meeting_request|unsubscribe|unknown",
                "confidence": 0.0-1.0,
                "reasoning": "why this intent was chosen",
                "next_action": "what the agent should do next"
            }
        """
        cache_key = f"intent:{hash(text[:200])}"
        cached = _cache_get(cache_key)
        if cached:
            logger.debug("LLM cache hit for intent classification")
            return cached

        # Use rule-based if rate limited
        if self._is_rate_limited():
            result = self._rule_based_intent(text)
            logger.info("Rate limited — rule-based intent: %s (%.2f)", result["intent"], result["confidence"])
            return result

        system_prompt = (
            "You are an expert sales AI classifying customer intent.\n"
            "Classify into EXACTLY one of: interested, not_interested, question, "
            "objection, callback_requested, meeting_request, unsubscribe, unknown.\n"
            "Respond with ONLY valid JSON:\n"
            '{"intent":"<value>","confidence":<0.0-1.0>,"reasoning":"<1 sentence>","next_action":"<what to do>"}'
        )
        user_prompt = f"Classify intent:\n\n{text}"
        if context:
            user_prompt += f"\n\nLead context: {context}"

        response = self._call_llm(system_prompt, user_prompt, temperature=0.1, max_tokens=150)

        if not response:
            result = self._rule_based_intent(text)
            logger.info("LLM unavailable — rule-based intent: %s", result["intent"])
            return result

        try:
            result = json.loads(response)
            _cache_set(cache_key, result)
            return result
        except (json.JSONDecodeError, KeyError):
            return self._rule_based_intent(text)

    def _rule_based_intent(self, text: str) -> Dict[str, Any]:
        """Weighted keyword scoring — used when LLM is unavailable."""
        text_lower = text.lower()

        patterns = {
            "interested":         [("interested", 0.8), ("tell me more", 0.9), ("sounds good", 0.7),
                                   ("yes please", 0.8), ("want to learn", 0.7), ("love to", 0.6),
                                   ("sign me up", 0.9), ("let's do it", 0.8), ("great", 0.5)],
            "not_interested":     [("not interested", 0.95), ("no thanks", 0.9), ("don't need", 0.8),
                                   ("already have", 0.7), ("happy with current", 0.8), ("pass", 0.5)],
            "question":           [("how does", 0.8), ("what is", 0.7), ("can you", 0.6),
                                   ("do you", 0.6), ("?", 0.4), ("how much", 0.8), ("pricing", 0.7)],
            "objection":          [("too expensive", 0.9), ("not now", 0.8), ("maybe later", 0.7),
                                   ("budget", 0.7), ("competitor", 0.6), ("contract", 0.6)],
            "callback_requested": [("call me", 0.9), ("give me a call", 0.95), ("callback", 0.9),
                                   ("call back", 0.9), ("reach me", 0.8)],
            "meeting_request":    [("schedule", 0.8), ("demo", 0.9), ("meeting", 0.8),
                                   ("book", 0.7), ("calendar", 0.7), ("show me", 0.6)],
            "unsubscribe":        [("unsubscribe", 0.99), ("opt out", 0.95), ("remove me", 0.9),
                                   ("stop emailing", 0.95), ("don't contact", 0.9)],
        }

        scores: Dict[str, float] = {k: 0.0 for k in patterns}
        for intent, kw_list in patterns.items():
            for keyword, weight in kw_list:
                if keyword in text_lower:
                    scores[intent] = max(scores[intent], weight)

        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]

        if best_score < 0.4:
            return {"intent": "unknown", "confidence": 0.3,
                    "reasoning": "No clear intent signals", "next_action": "escalate to human"}

        action_map = {
            "interested":         "schedule a demo or send more information",
            "not_interested":     "mark as not interested and stop outreach",
            "question":           "answer the question and offer a demo",
            "objection":          "address the objection with relevant information",
            "callback_requested": "schedule a callback",
            "meeting_request":    "send available demo slots immediately",
            "unsubscribe":        "unsubscribe and send confirmation",
        }
        return {
            "intent": best_intent,
            "confidence": best_score,
            "reasoning": f"Detected '{best_intent}' signals in message",
            "next_action": action_map.get(best_intent, "follow up"),
        }

    # ------------------------------------------------------------------
    # Next action reasoning — LLM with rule-based fallback
    # ------------------------------------------------------------------

    def reason_next_action(
        self,
        lead_summary: str,
        interaction_history: str,
        available_actions: List[str],
    ) -> Dict[str, Any]:
        """LLM reasons about the best next action for a lead.

        Falls back to smart rule-based logic when rate limited.

        Returns:
            {
                "action": "<chosen action>",
                "reasoning": "<why>",
                "urgency": "high|medium|low",
                "message_hint": "<tone/content hint>"
            }
        """
        if not available_actions:
            return {"action": "end", "reasoning": "No actions available",
                    "urgency": "low", "message_hint": ""}

        cache_key = f"action:{hash(lead_summary[:150] + interaction_history[:100])}"
        cached = _cache_get(cache_key)
        if cached:
            logger.debug("LLM cache hit for action reasoning")
            return cached

        # Use rule-based if rate limited
        if self._is_rate_limited():
            result = self._rule_based_action(lead_summary, available_actions)
            logger.info("Rate limited — rule-based action: %s", result["action"])
            return result

        system_prompt = (
            "You are a sales orchestration AI. Decide the best next action for a lead.\n"
            "Think: What stage is this lead? What was the last interaction? "
            "What would a skilled sales rep do?\n"
            "Respond with ONLY valid JSON:\n"
            '{"action":"<from available>","reasoning":"<2 sentences>","urgency":"high|medium|low","message_hint":"<tone hint>"}'
        )
        user_prompt = (
            f"Lead:\n{lead_summary}\n\n"
            f"History:\n{interaction_history}\n\n"
            f"Available actions: {', '.join(available_actions)}\n\n"
            "Best next action?"
        )

        response = self._call_llm(system_prompt, user_prompt, temperature=0.3, max_tokens=200)

        if not response:
            result = self._rule_based_action(lead_summary, available_actions)
            return result

        try:
            result = json.loads(response)
            if result.get("action") not in available_actions:
                result["action"] = available_actions[0]
            _cache_set(cache_key, result)
            return result
        except (json.JSONDecodeError, KeyError):
            return self._rule_based_action(lead_summary, available_actions)

    def _rule_based_action(self, lead_summary: str, available_actions: List[str]) -> Dict[str, Any]:
        """Smart rule-based action selection — used when LLM is unavailable."""
        summary_lower = lead_summary.lower()

        # Priority-based selection from available actions
        priority_order = ["schedule_demo", "cold_call", "follow_up", "send_email", "escalate"]

        for preferred in priority_order:
            if preferred in available_actions:
                return {
                    "action": preferred,
                    "reasoning": f"Rule-based: '{preferred}' is the highest priority available action for this lead stage.",
                    "urgency": "medium",
                    "message_hint": "Be professional, warm, and concise. Focus on value.",
                }

        return {
            "action": available_actions[0],
            "reasoning": "Defaulting to first available action.",
            "urgency": "low",
            "message_hint": "Be professional and helpful.",
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
        """Generate a personalized email subject + body.

        Returns: {"subject": "...", "body": "..."}
        Falls back to smart templates when LLM unavailable.
        """
        if self._is_rate_limited():
            return self._template_email(lead_name, company, intent)

        system_prompt = (
            "You are Priya, a warm sales rep at Pebble POS (AI-native POS for restaurants/retail).\n"
            "Write personalized, human-sounding sales emails. Under 150 words. "
            "End with a low-pressure CTA.\n"
            'Respond with ONLY valid JSON: {"subject":"<subject>","body":"<body with \\n line breaks>"}'
        )
        user_prompt = (
            f"Write email to: {lead_name} at {company}\n"
            f"Stage: {intent}\nContext: {context}\nHint: {template_hint}"
        )

        response = self._call_llm(system_prompt, user_prompt, temperature=0.7, max_tokens=350)

        if not response:
            return self._template_email(lead_name, company, intent)

        try:
            return json.loads(response)
        except (json.JSONDecodeError, KeyError):
            return self._template_email(lead_name, company, intent)

    def _template_email(self, lead_name: str, company: str, intent: str) -> Dict[str, str]:
        """Smart email templates — used when LLM is unavailable."""
        first = lead_name.split()[0] if lead_name else "there"
        comp = f" at {company}" if company else ""

        templates = {
            "new": {
                "subject": f"Quick question about your POS{comp}, {first}",
                "body": (
                    f"Hi {first},\n\n"
                    f"I'm Priya from Pebble — we help restaurants and retail stores with their POS, "
                    f"online ordering, loyalty, and AI, all from one platform.\n\n"
                    f"Quick question: are you happy with your current setup, or is there something "
                    f"you wish it did better?\n\n"
                    f"Would love to show you a quick 15-min demo — no commitment at all.\n\n"
                    f"Best,\nPriya\nPebble | customercare@pebbletab.com"
                ),
            },
            "contacted": {
                "subject": f"Following up, {first}",
                "body": (
                    f"Hi {first},\n\n"
                    f"Just following up on my previous message. I know things get busy!\n\n"
                    f"Pebble has helped restaurants like yours increase repeat visits by 23% "
                    f"with our loyalty and AI features.\n\n"
                    f"Would 15 minutes this week work for a quick demo?\n\n"
                    f"Best,\nPriya"
                ),
            },
            "interested": {
                "subject": f"Let's find a time, {first}!",
                "body": (
                    f"Hi {first},\n\n"
                    f"Great to hear you're interested! I'd love to show you Pebble in action.\n\n"
                    f"Here are a few times that work this week:\n"
                    f"- Tomorrow at 10am\n- Wednesday at 2pm\n- Thursday at 11am\n\n"
                    f"Or book directly: https://pebble.prod.xenvoice.com/book-a-demo\n\n"
                    f"Best,\nPriya"
                ),
            },
            "demo_scheduling": {
                "subject": f"Your Pebble demo — pick a time, {first}",
                "body": (
                    f"Hi {first},\n\n"
                    f"I'd love to show you how Pebble can help {company or 'your business'}.\n\n"
                    f"The demo is 15 minutes, completely free, and I'll show you exactly "
                    f"how it works for your type of business.\n\n"
                    f"Book here: https://pebble.prod.xenvoice.com/book-a-demo\n\n"
                    f"Best,\nPriya"
                ),
            },
        }

        template = templates.get(intent, templates["new"])
        return template

    def generate_call_script(
        self,
        lead_name: str,
        company: str,
        context: str = "",
        rag_context: str = "",
    ) -> str:
        """Generate a personalized call opening script."""
        if self._is_rate_limited():
            return self._template_call_script(lead_name, company)

        system_prompt = (
            "Write a cold call opening for Priya at Pebble POS. "
            "Sound 100% human — warm, natural, under 3 sentences. "
            "End with an engaging question."
        )
        user_prompt = (
            f"Call to: {lead_name} at {company}\n"
            f"Context: {context}\nProduct knowledge: {rag_context[:300]}"
        )

        response = self._call_llm(system_prompt, user_prompt, temperature=0.8, max_tokens=120)
        return response if response else self._template_call_script(lead_name, company)

    def _template_call_script(self, lead_name: str, company: str) -> str:
        name = lead_name or "there"
        comp = f" at {company}" if company else ""
        return (
            f"Hi, am I speaking with {name}? "
            f"This is Priya calling from Pebble{comp}. "
            f"We help restaurants and retail stores run their POS, ordering, loyalty, and AI "
            f"all from one platform — do you have just 2 minutes?"
        )

    def generate_inbound_reply(
        self,
        message: str,
        lead_name: str,
        intent: str,
        rag_context: str = "",
        interaction_history: str = "",
    ) -> str:
        """Generate a contextual reply to an inbound message."""
        if self._is_rate_limited():
            return self._template_reply(lead_name, intent)

        system_prompt = (
            f"You are Priya, a helpful sales rep at Pebble POS.\n"
            f"Answer using the product knowledge provided. Be warm, concise, under 120 words.\n\n"
            f"PRODUCT KNOWLEDGE:\n{rag_context}\n\n"
            f"CONVERSATION HISTORY:\n{interaction_history}"
        )
        user_prompt = f"Customer {lead_name} (intent: {intent}) says:\n{message}\n\nWrite a helpful reply."

        response = self._call_llm(system_prompt, user_prompt, temperature=0.6, max_tokens=180)
        return response if response else self._template_reply(lead_name, intent)

    def _template_reply(self, lead_name: str, intent: str) -> str:
        first = lead_name.split()[0] if lead_name else "there"
        replies = {
            "interested":         f"Hi {first}, great to hear you're interested! I'd love to show you Pebble in action. Can I send you some available demo times?",
            "question":           f"Hi {first}, happy to answer your questions! Pebble is an all-in-one POS for restaurants and retail — POS, online ordering, loyalty, and AI in one platform. What specifically would you like to know?",
            "objection":          f"Hi {first}, I completely understand. Many of our customers had the same concern before trying Pebble. Would a quick 15-min demo help address that?",
            "callback_requested": f"Hi {first}, absolutely! I'll have someone from our team call you shortly. What's the best time to reach you?",
            "meeting_request":    f"Hi {first}, I'd love to schedule a demo! Here's my booking link: https://pebble.prod.xenvoice.com/book-a-demo — pick any time that works for you.",
            "not_interested":     f"Hi {first}, no problem at all! Feel free to reach out anytime if things change. Wishing you all the best!",
        }
        return replies.get(intent, f"Hi {first}, thanks for reaching out! I'll get back to you shortly with more details.")

    def answer_inbound_call_question(
        self,
        question: str,
        caller_name: str,
        rag_context: str,
        conversation_history: str = "",
    ) -> str:
        """Answer an inbound call question using RAG-retrieved product knowledge."""
        if self._is_rate_limited():
            return self._template_call_answer(caller_name, question)

        system_prompt = (
            f"You are an AI assistant for Pebble POS answering an inbound call.\n"
            f"Answer accurately using ONLY the product knowledge below. "
            f"Be conversational, 2-3 sentences max.\n\n"
            f"PRODUCT KNOWLEDGE:\n{rag_context}\n\n"
            f"CONVERSATION:\n{conversation_history}"
        )
        user_prompt = f"Caller ({caller_name}) asks: {question}"

        response = self._call_llm(system_prompt, user_prompt, temperature=0.4, max_tokens=130)
        return response if response else self._template_call_answer(caller_name, question)

    def _template_call_answer(self, caller_name: str, question: str) -> str:
        name = caller_name or "there"
        q = question.lower()
        if "price" in q or "cost" in q or "how much" in q:
            return f"Hi {name}! Pebble starts at $99/month for our Starter plan. We also have Growth at $199 and Pro at $349. All plans include free onboarding and 24/7 support. Would you like me to connect you with our team for a personalized quote?"
        if "integrat" in q or "doordash" in q or "uber" in q:
            return f"Great question! Pebble integrates with DoorDash, Uber Eats, Grubhub, QuickBooks, and all major payment processors. Orders flow directly into your POS automatically."
        if "demo" in q or "trial" in q or "try" in q:
            return f"Absolutely! You can book a free 15-minute demo at pebble.prod.xenvoice.com/book-a-demo. No commitment required — we'll show you the full platform live."
        return f"Thanks for calling Pebble, {name}! I'd be happy to help. For detailed information, let me connect you with one of our specialists who can answer all your questions."

    # ------------------------------------------------------------------
    # Internal: unified LLM call
    # ------------------------------------------------------------------

    def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.5,
        max_tokens: int = 300,
    ) -> str:
        """Call Groq, fall back to OpenAI, return empty string if both fail."""
        if self._groq_key:
            result = self._call_groq(system_prompt, user_prompt, temperature, max_tokens)
            if result:
                return result

        if self._openai_key:
            result = self._call_openai(system_prompt, user_prompt, temperature, max_tokens)
            if result:
                return result

        return ""

    def _call_groq(self, system: str, user: str, temperature: float, max_tokens: int) -> str:
        try:
            import requests
            resp = requests.post(
                f"{self.GROQ_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {self._groq_key}", "Content-Type": "application/json"},
                json={
                    "model": self.GROQ_MODEL,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            if resp.status_code == 429:
                self._last_rate_limit_ts = time.time()
                logger.info("Groq rate limited — switching to rule-based for %ds", self._rate_limit_backoff)
            else:
                logger.warning("Groq error %d: %s", resp.status_code, resp.text[:80])
        except Exception as e:
            logger.warning("Groq call failed: %s", e)
        return ""

    def _call_openai(self, system: str, user: str, temperature: float, max_tokens: int) -> str:
        try:
            import requests
            resp = requests.post(
                f"{self.OPENAI_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {self._openai_key}", "Content-Type": "application/json"},
                json={
                    "model": self.OPENAI_MODEL,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            logger.warning("OpenAI error %d: %s", resp.status_code, resp.text[:80])
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
