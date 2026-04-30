"""Lead Scorer — LLM-powered lead scoring and sentiment tracking.

Scores each lead 0-100 based on:
- Engagement history (calls answered, emails opened, replies)
- Intent signals (interested, question, objection)
- Response speed (how quickly they reply)
- Company signals (size, industry)
- Sentiment trend (warming up or cooling down)

Orchestrator uses scores to prioritize high-value leads.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LeadScorer:
    """Scores leads and tracks sentiment trends over time."""

    def __init__(self) -> None:
        from app.core.agent_llm import get_agent_llm
        self._llm = get_agent_llm()

    def score_lead(self, lead: Any, interactions: List[Any]) -> Dict[str, Any]:
        """Score a lead 0-100 and return detailed breakdown.

        Returns:
            {
                "score": 0-100,
                "grade": "A/B/C/D/F",
                "sentiment": "warming/neutral/cooling",
                "urgency": "high/medium/low",
                "reasoning": "...",
                "recommended_action": "..."
            }
        """
        # Build scoring context
        score = 0
        factors = []

        # 1. Status score (0-30 points)
        status_scores = {
            "new": 10,
            "contacted": 15,
            "interested": 28,
            "follow_up_scheduled": 25,
            "demo_scheduled": 30,
            "demo_completed": 28,
            "converted": 30,
            "not_interested": 2,
            "unsubscribed": 0,
            "do_not_contact": 0,
            "requires_human_review": 5,
        }
        status_val = lead.status.value if hasattr(lead.status, "value") else str(lead.status)
        status_score = status_scores.get(status_val, 10)
        score += status_score
        factors.append(f"Status ({status_val}): +{status_score}")

        # 2. Engagement score (0-25 points)
        call_attempts = lead.call_attempts or 0
        email_attempts = lead.email_attempts or 0
        total_attempts = call_attempts + email_attempts

        if total_attempts == 0:
            eng_score = 5  # fresh lead
        elif total_attempts <= 2:
            eng_score = 15
        elif total_attempts <= 4:
            eng_score = 20
        else:
            eng_score = max(0, 25 - (total_attempts - 4) * 3)  # diminishing returns

        score += eng_score
        factors.append(f"Engagement ({total_attempts} touches): +{eng_score}")

        # 3. Interaction quality score (0-25 points)
        if interactions:
            positive_outcomes = sum(1 for i in interactions
                                    if i.outcome in ("interested", "demo_booked", "replied", "answered"))
            negative_outcomes = sum(1 for i in interactions
                                    if i.outcome in ("not_interested", "escalated", "suppressed"))
            quality_score = min(25, positive_outcomes * 8 - negative_outcomes * 5)
            quality_score = max(0, quality_score)
            score += quality_score
            factors.append(f"Interaction quality (+{positive_outcomes} pos, -{negative_outcomes} neg): +{quality_score}")

        # 4. Recency score (0-10 points)
        if lead.last_contacted_at:
            now = datetime.now(timezone.utc)
            lc = lead.last_contacted_at
            if lc.tzinfo is None:
                lc = lc.replace(tzinfo=timezone.utc)
            hours_since = (now - lc).total_seconds() / 3600
            if hours_since < 24:
                recency_score = 10
            elif hours_since < 72:
                recency_score = 7
            elif hours_since < 168:
                recency_score = 4
            else:
                recency_score = 1
            score += recency_score
            factors.append(f"Recency ({hours_since:.0f}h ago): +{recency_score}")

        # 5. Data completeness (0-10 points)
        completeness = 0
        if lead.email:
            completeness += 3
        if lead.phone:
            completeness += 3
        if lead.company:
            completeness += 2
        if lead.first_name and lead.last_name:
            completeness += 2
        score += completeness
        factors.append(f"Data completeness: +{completeness}")

        score = min(100, max(0, score))

        # Grade
        if score >= 80:
            grade = "A"
        elif score >= 65:
            grade = "B"
        elif score >= 45:
            grade = "C"
        elif score >= 25:
            grade = "D"
        else:
            grade = "F"

        # Sentiment trend from recent interactions
        sentiment = self._calculate_sentiment(interactions)

        # Urgency
        if score >= 70 or sentiment == "warming":
            urgency = "high"
        elif score >= 40:
            urgency = "medium"
        else:
            urgency = "low"

        # Recommended action
        recommended = self._recommend_action(lead, score, sentiment, interactions)

        return {
            "score": score,
            "grade": grade,
            "sentiment": sentiment,
            "urgency": urgency,
            "factors": factors,
            "recommended_action": recommended,
        }

    def _calculate_sentiment(self, interactions: List[Any]) -> str:
        """Calculate sentiment trend from last 5 interactions."""
        if not interactions:
            return "neutral"

        recent = interactions[-5:]
        positive = sum(1 for i in recent
                       if i.outcome in ("interested", "demo_booked", "replied", "answered", "qualified"))
        negative = sum(1 for i in recent
                       if i.outcome in ("not_interested", "escalated", "no_answer", "voicemail"))

        if positive > negative:
            return "warming"
        elif negative > positive:
            return "cooling"
        return "neutral"

    def _recommend_action(
        self,
        lead: Any,
        score: int,
        sentiment: str,
        interactions: List[Any],
    ) -> str:
        status = lead.status.value if hasattr(lead.status, "value") else str(lead.status)

        if status == "interested":
            return "schedule_demo — lead is ready"
        if status == "demo_scheduled":
            return "send_reminder — demo coming up"
        if sentiment == "warming" and score >= 50:
            return "cold_call — momentum is building, strike now"
        if sentiment == "cooling" and score < 30:
            return "send_email — low-pressure re-engagement"
        if score >= 70:
            return "cold_call — high-value lead, prioritize"
        if score >= 40:
            return "follow_up — steady engagement needed"
        return "send_email — nurture with content"


# Singleton
_scorer: Optional[LeadScorer] = None


def get_lead_scorer() -> LeadScorer:
    global _scorer
    if _scorer is None:
        _scorer = LeadScorer()
    return _scorer
