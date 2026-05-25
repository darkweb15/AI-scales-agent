"""AI Chat endpoint — powers the dashboard AI Assistant bar."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.agent_llm import get_agent_llm

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    context: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    suggestions: list[str] = []


@router.post("/ask", response_model=ChatResponse)
async def ai_chat(req: ChatRequest):
    """Answer a sales-related question using the LLM."""
    llm = get_agent_llm()

    system_prompt = (
        "You are a helpful AI sales assistant for Pebble POS.\n"
        "Answer questions about leads, pipeline, sales strategy, and performance.\n"
        "Be concise (2-4 sentences). Give actionable insights.\n"
        "If the question is about specific data, provide your best analysis.\n\n"
        "After your answer, suggest 2 follow-up questions the user might ask.\n\n"
        "Respond with ONLY valid JSON:\n"
        '{"answer":"<your answer>","suggestions":["<follow-up 1>","<follow-up 2>"]}'
    )
    user_prompt = f"Question: {req.question}"
    if req.context:
        user_prompt += f"\n\nContext: {req.context}"

    import json
    response = llm._call_llm_with_retry(
        system_prompt, user_prompt, temperature=0.5, max_tokens=300
    )

    if not response:
        return ChatResponse(
            answer="I'm having trouble connecting to the AI service right now. Please try again in a moment.",
            suggestions=["What leads should I prioritize?", "Show me pipeline health"],
        )

    try:
        data = json.loads(response)
        return ChatResponse(
            answer=data.get("answer", response),
            suggestions=data.get("suggestions", []),
        )
    except (json.JSONDecodeError, KeyError):
        return ChatResponse(answer=response, suggestions=[])
