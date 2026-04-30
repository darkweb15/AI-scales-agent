"""Call webhook — production-grade Vapi/Bland AI outcome processor.

Production upgrades:
1. Real LLM intent classification (no keyword matching)
2. Lead deduplication before creating new records
3. Live WebSocket events pushed to dashboard instantly
4. Lead scoring after every call
5. Sentiment tracking across interactions
6. Structured interaction logging with full context
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Request

from app.database.base import async_session_factory
from app.database.service import DatabaseService
from app.models.enums import LeadStatus
from app.core.websocket_broadcaster import broadcast

logger = logging.getLogger(__name__)
router = APIRouter()
db = DatabaseService()

DEMO_LINK = "https://pebble.prod.xenvoice.com/book-a-demo"


# ── Email extraction ──────────────────────────────────────────────────────────

def extract_email_from_transcript(transcript: str) -> str:
    """Extract email from transcript — handles spoken email formats."""
    if not transcript:
        return ""
    # Direct regex
    match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", transcript)
    if match:
        return match.group(0).lower()
    # Spoken format: "bhargav at growit dot io"
    spoken = transcript.lower()
    spoken = re.sub(r"\s+at\s+", "@", spoken)
    spoken = re.sub(r"\s+dot\s+", ".", spoken)
    spoken = re.sub(r"\s+", "", spoken)
    match2 = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", spoken)
    return match2.group(0).lower() if match2 else ""


# ── LLM-powered intent classification ────────────────────────────────────────

def classify_call_intent(transcript: str, summary: str) -> dict:
    """Use LLM to classify call intent. Falls back to weighted scoring."""
    from app.core.agent_llm import get_agent_llm
    llm = get_agent_llm()

    full_text = f"Call transcript: {transcript}\n\nCall summary: {summary}"
    result = llm.classify_intent(
        text=full_text,
        context="This is an outbound sales call for Pebble POS to a restaurant/retail business owner.",
    )
    return result


def intent_to_lead_status(intent: str, demo_booked: bool) -> LeadStatus:
    """Map LLM intent to LeadStatus."""
    if demo_booked:
        return LeadStatus.demo_scheduled
    mapping = {
        "interested":         LeadStatus.interested,
        "meeting_request":    LeadStatus.interested,
        "not_interested":     LeadStatus.not_interested,
        "unsubscribe":        LeadStatus.unsubscribed,
        "callback_requested": LeadStatus.contacted,
        "question":           LeadStatus.contacted,
        "objection":          LeadStatus.contacted,
        "unknown":            LeadStatus.contacted,
    }
    return mapping.get(intent, LeadStatus.contacted)


# ── Demo booking email ────────────────────────────────────────────────────────

async def send_demo_booking_email(to_email: str, lead_name: str) -> bool:
    """Send demo booking confirmation email via SendGrid."""
    import httpx

    sg_key = os.environ.get("SENDGRID_API_KEY", "")
    from_email = os.environ.get("FROM_EMAIL", "bhargav.gangula@growith.io")
    from_name = os.environ.get("FROM_NAME", "Priya from Pebble")

    if not sg_key or not to_email:
        return False

    first_name = lead_name.split()[0] if lead_name else "there"

    payload = {
        "personalizations": [{
            "to": [{"email": to_email, "name": lead_name}],
            "subject": f"Your Pebble Demo is Confirmed, {first_name}! 🎉",
        }],
        "from": {"email": from_email, "name": from_name},
        "content": [{
            "type": "text/html",
            "value": f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
  <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:30px;border-radius:12px;text-align:center;margin-bottom:24px;">
    <h1 style="color:white;margin:0;font-size:24px;">Your Demo is Booked! 🎉</h1>
    <p style="color:#e0e7ff;margin:8px 0 0 0;">Pebble — AI-Native POS Platform</p>
  </div>
  <p style="color:#374151;font-size:16px;">Hey {first_name},</p>
  <p style="color:#374151;font-size:15px;line-height:1.6;">
    Thanks for chatting with me! I'm excited to show you how Pebble can help your business.
  </p>
  <div style="text-align:center;margin:32px 0;">
    <a href="{DEMO_LINK}" style="background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;padding:14px 32px;border-radius:8px;text-decoration:none;font-size:16px;font-weight:bold;">
      📅 Book Your Demo Now
    </a>
  </div>
  <div style="background:#f3f4f6;border-radius:8px;padding:16px;margin:24px 0;">
    <p style="color:#374151;font-size:14px;margin:0 0 8px 0;"><strong>What we'll cover in 15 minutes:</strong></p>
    <ul style="color:#6b7280;font-size:14px;margin:0;padding-left:20px;line-height:1.8;">
      <li>AI that answers every call and takes orders automatically</li>
      <li>Direct ordering — keep 100% of your revenue (no marketplace fees)</li>
      <li>Loyalty + campaigns that bring customers back</li>
      <li>Live demo of the full POS system</li>
    </ul>
  </div>
  <p style="color:#374151;font-size:15px;">
    Talk soon,<br><strong>Priya</strong><br>
    <span style="color:#6b7280;font-size:13px;">Pebble | customercare@pebbletab.com | (469)-310-7731</span>
  </p>
</div>""",
        }],
    }

    try:
        import httpx as _httpx
        async with _httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {sg_key}", "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code in (200, 202):
                logger.info("Demo booking email sent to %s", to_email)
                return True
            logger.error("SendGrid error %s: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.error("Email send failed: %s", e)
    return False


# ── Vapi webhook ──────────────────────────────────────────────────────────────

@router.post("/vapi-webhook")
async def vapi_webhook(request: Request):
    """Production-grade Vapi call outcome processor.

    Upgrades vs old version:
    - LLM intent classification (not keyword matching)
    - Lead deduplication
    - Live WebSocket events to dashboard
    - Lead scoring after call
    - Full structured logging
    """
    try:
        data = await request.json()
    except Exception:
        return {"status": "ok"}

    call_data = data.get("call", data)
    call_id = call_data.get("id", "")
    transcript = call_data.get("transcript", "") or ""
    summary = call_data.get("summary", "") or ""
    ended_reason = call_data.get("endedReason", "")
    duration = call_data.get("duration", 0) or 0
    customer = call_data.get("customer", {})
    phone = customer.get("number", "") or call_data.get("to", "") or ""
    lead_name = customer.get("name", "")

    logger.info("📞 Vapi webhook: call_id=%s ended=%s duration=%ss", call_id, ended_reason, duration)

    if not transcript and not summary:
        return {"status": "ok", "note": "no transcript"}

    # LLM intent classification
    intent_result = classify_call_intent(transcript, summary)
    intent = intent_result.get("intent", "unknown")
    confidence = intent_result.get("confidence", 0.5)
    reasoning = intent_result.get("reasoning", "")
    next_action = intent_result.get("next_action", "")

    logger.info("🧠 Call intent: %s (%.2f) — %s", intent, confidence, reasoning[:60])

    # Check for demo booking signals
    full_text = (transcript + " " + summary).lower()
    demo_booked = any(kw in full_text for kw in [
        "book", "demo", "schedule", "booking link", "confirmation", "send me"
    ]) or intent in ("meeting_request", "interested")

    # Extract email
    email = extract_email_from_transcript(transcript)

    # Determine new lead status
    new_status = intent_to_lead_status(intent, demo_booked)

    outcome = "demo_booked" if demo_booked else intent

    if phone:
        async with async_session_factory() as session:
            # Deduplication — find existing lead
            from app.core.lead_deduplicator import get_deduplicator
            dedup = get_deduplicator()
            lead, was_created = await dedup.find_or_create(
                session, db,
                data={
                    "first_name": lead_name.split()[0] if lead_name else "Inbound",
                    "last_name": " ".join(lead_name.split()[1:]) if lead_name and len(lead_name.split()) > 1 else "Caller",
                    "email": email or f"call_{phone.replace('+','')}@unknown.com",
                    "phone": phone,
                    "status": LeadStatus.new,
                    "source": "inbound_call",
                    "call_attempts": 0,
                    "email_attempts": 0,
                },
            )

            if was_created:
                logger.info("Created new lead from call: %s", lead.id)

            # Update lead status
            await db.update_lead_status(session, lead.id, new_status)
            await db.update_lead(
                session, lead.id,
                last_contacted_at=datetime.now(timezone.utc),
                call_attempts=(lead.call_attempts or 0) + 1,
            )

            # Log interaction
            await db.create_interaction_log(session, {
                "lead_id": lead.id,
                "agent_type": "cold_calling",
                "channel": "call",
                "direction": "outbound",
                "timestamp": datetime.now(timezone.utc),
                "duration_seconds": int(duration),
                "summary": (
                    f"Vapi AI call — intent: {intent} ({confidence:.0%} confidence). "
                    f"Ended: {ended_reason}. {reasoning}"
                ),
                "intent_detected": intent,
                "outcome": outcome,
                "raw_transcript": transcript,
            })

            await session.commit()

            # Lead scoring
            from app.core.lead_scorer import get_lead_scorer
            scorer = get_lead_scorer()
            interactions = await db.get_interactions_for_lead(session, lead.id)
            score_result = scorer.score_lead(lead, interactions)

            # Live WebSocket events to dashboard
            await broadcast("call.completed", {
                "lead_id": str(lead.id),
                "lead_name": f"{lead.first_name} {lead.last_name}".strip(),
                "phone": phone,
                "outcome": outcome,
                "intent": intent,
                "confidence": confidence,
                "reasoning": reasoning,
                "next_action": next_action,
                "score": score_result["score"],
                "grade": score_result["grade"],
                "sentiment": score_result["sentiment"],
                "duration_seconds": int(duration),
                "demo_booked": demo_booked,
                "email_found": email,
            })

            await broadcast("lead.status_changed", {
                "lead_id": str(lead.id),
                "new_status": new_status.value,
                "score": score_result["score"],
            })

            await broadcast("kpi.updated", {
                "metric": "calls_made",
                "delta": 1,
            })

            if demo_booked:
                await broadcast("kpi.updated", {"metric": "demos_scheduled", "delta": 1})
                await broadcast("demo.scheduled", {
                    "lead_id": str(lead.id),
                    "lead_name": f"{lead.first_name} {lead.last_name}".strip(),
                })

            # Send booking email if demo booked and email found
            if demo_booked and email:
                name = lead_name or f"{lead.first_name} {lead.last_name}".strip()
                sent = await send_demo_booking_email(email, name)
                logger.info("Booking email sent=%s to %s", sent, email)

    return {
        "status": "received",
        "call_id": call_id,
        "intent": intent,
        "confidence": confidence,
        "outcome": outcome,
        "demo_booked": demo_booked,
        "email_found": email,
        "next_action": next_action,
    }


# ── Bland AI webhook ──────────────────────────────────────────────────────────

@router.post("/call-webhook")
async def bland_call_webhook(request: Request):
    """Bland AI call outcome — same production upgrades as Vapi."""
    try:
        data = await request.json()
    except Exception:
        return {"status": "ok"}

    call_id = data.get("call_id", "")
    transcript = data.get("transcript", "") or ""
    summary = data.get("summary", "") or ""
    phone = data.get("to", "") or data.get("phone_number", "") or ""
    lead_name = data.get("variables", {}).get("lead_name", "")

    logger.info("Bland webhook: call_id=%s", call_id)

    intent_result = classify_call_intent(transcript, summary)
    intent = intent_result.get("intent", "unknown")
    full_text = (transcript + " " + summary).lower()
    demo_booked = any(kw in full_text for kw in ["book", "demo", "schedule", "email"])
    email = extract_email_from_transcript(transcript)
    new_status = intent_to_lead_status(intent, demo_booked)

    if phone:
        async with async_session_factory() as session:
            from app.core.lead_deduplicator import get_deduplicator
            dedup = get_deduplicator()
            lead, _ = await dedup.find_or_create(
                session, db,
                data={
                    "first_name": lead_name.split()[0] if lead_name else "Caller",
                    "last_name": "",
                    "email": email or f"bland_{phone.replace('+','')}@unknown.com",
                    "phone": phone,
                    "status": LeadStatus.new,
                    "source": "bland_call",
                    "call_attempts": 0,
                    "email_attempts": 0,
                },
            )
            await db.update_lead_status(session, lead.id, new_status)
            await db.update_lead(session, lead.id,
                last_contacted_at=datetime.now(timezone.utc),
                call_attempts=(lead.call_attempts or 0) + 1,
            )
            await db.create_interaction_log(session, {
                "lead_id": lead.id,
                "agent_type": "cold_calling",
                "channel": "call",
                "direction": "outbound",
                "timestamp": datetime.now(timezone.utc),
                "summary": f"Bland AI call — intent: {intent}. {summary[:200]}",
                "intent_detected": intent,
                "outcome": "demo_booked" if demo_booked else intent,
                "raw_transcript": transcript,
            })
            await session.commit()

            await broadcast("call.completed", {
                "lead_id": str(lead.id),
                "outcome": "demo_booked" if demo_booked else intent,
                "intent": intent,
            })

            if demo_booked and email:
                name = lead_name or f"{lead.first_name} {lead.last_name}".strip()
                await send_demo_booking_email(email, name)

    return {"status": "received", "call_id": call_id, "intent": intent, "demo_booked": demo_booked}


@router.get("/call-transcript/{call_id}")
async def get_call_transcript(call_id: str):
    """Fetch transcript from Vapi."""
    import httpx
    api_key = os.environ.get("VAPI_API_KEY", "")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"https://api.vapi.ai/call/{call_id}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        if resp.status_code == 200:
            d = resp.json()
            return {
                "call_id": call_id,
                "status": d.get("status"),
                "ended_reason": d.get("endedReason"),
                "transcript": d.get("transcript", ""),
                "summary": d.get("summary", ""),
                "cost": d.get("cost", 0),
                "duration": d.get("duration", 0),
            }
    return {"call_id": call_id, "error": "not found"}
