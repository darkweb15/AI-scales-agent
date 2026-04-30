"""Call webhook — handles post-call outcomes from Vapi and Bland AI.

When a call ends:
1. Parses transcript to detect demo booking + email address
2. Updates lead status in DB
3. Sends real booking confirmation email via SendGrid
4. Logs the interaction
"""
from __future__ import annotations

import logging
import os
import re
from fastapi import APIRouter, Request
from app.database.base import async_session_factory
from app.database.service import DatabaseService
from app.models.enums import LeadStatus

logger = logging.getLogger(__name__)
router = APIRouter()
db = DatabaseService()

DEMO_LINK = "https://pebble.prod.xenvoice.com/book-a-demo"


# ── Email extraction ──────────────────────────────────────────────────────────

def extract_email_from_transcript(transcript: str) -> str:
    """Try to find an email address in the call transcript."""
    if not transcript:
        return ""

    # Direct regex match first
    match = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", transcript)
    if match:
        return match.group(0).lower()

    # Vapi sometimes spells out emails like "bhargav at growit dot io"
    spoken = transcript.lower()
    spoken = re.sub(r"\s+at\s+", "@", spoken)
    spoken = re.sub(r"\s+dot\s+", ".", spoken)
    spoken = re.sub(r"\s+", "", spoken)
    match2 = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", spoken)
    if match2:
        return match2.group(0).lower()

    return ""


# ── Email sender ──────────────────────────────────────────────────────────────

async def send_demo_booking_email(to_email: str, lead_name: str) -> bool:
    """Send demo booking confirmation email via SendGrid."""
    import httpx

    sg_key = os.environ.get("SENDGRID_API_KEY", "")
    from_email = os.environ.get("FROM_EMAIL", "bhargav.gangula@growith.io")
    from_name = os.environ.get("FROM_NAME", "Priya from Pebble")

    if not sg_key or not to_email:
        logger.warning("SendGrid key or email missing — skipping email")
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
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 24px;">
    <h1 style="color: white; margin: 0; font-size: 24px;">Your Demo is Booked! 🎉</h1>
    <p style="color: #e0e7ff; margin: 8px 0 0 0;">Pebble — AI-Native POS Platform</p>
  </div>

  <p style="color: #374151; font-size: 16px;">Hey {first_name},</p>

  <p style="color: #374151; font-size: 15px; line-height: 1.6;">
    Thanks for chatting with me earlier! I'm excited to show you how Pebble can help your business.
  </p>

  <p style="color: #374151; font-size: 15px; line-height: 1.6;">
    Click the button below to pick a time that works for you — the demo is just 15 minutes and completely free:
  </p>

  <div style="text-align: center; margin: 32px 0;">
    <a href="{DEMO_LINK}" style="background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-size: 16px; font-weight: bold;">
      📅 Book Your Demo Now
    </a>
  </div>

  <div style="background: #f3f4f6; border-radius: 8px; padding: 16px; margin: 24px 0;">
    <p style="color: #374151; font-size: 14px; margin: 0 0 8px 0;"><strong>What we'll cover in 15 minutes:</strong></p>
    <ul style="color: #6b7280; font-size: 14px; margin: 0; padding-left: 20px; line-height: 1.8;">
      <li>How Pebble's AI answers every call automatically</li>
      <li>Direct ordering — keep 100% of your revenue (no marketplace fees)</li>
      <li>Loyalty + campaigns that bring customers back</li>
      <li>Live demo of the POS system</li>
    </ul>
  </div>

  <p style="color: #374151; font-size: 15px; line-height: 1.6;">
    Any questions before the demo? Just reply to this email — I'm here to help!
  </p>

  <p style="color: #374151; font-size: 15px;">
    Talk soon,<br>
    <strong>Priya</strong><br>
    <span style="color: #6b7280; font-size: 13px;">Pebble Sales Team | customercare@pebbletab.com | (469)-310-7731</span>
  </p>

  <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;">
  <p style="color: #9ca3af; font-size: 12px; text-align: center;">
    Pebble — All-in-one POS for restaurants and retail stores<br>
    <a href="{DEMO_LINK}" style="color: #6366f1;">{DEMO_LINK}</a>
  </p>
</div>
""",
        }],
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {sg_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code in (200, 202):
                logger.info("Demo booking email sent to %s", to_email)
                return True
            else:
                logger.error("SendGrid error %s: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.error("Email send failed: %s", e)

    return False


# ── Vapi webhook ──────────────────────────────────────────────────────────────

@router.post("/vapi-webhook")
async def vapi_webhook(request: Request):
    """Receives call outcome from Vapi after each call ends."""
    try:
        data = await request.json()
    except Exception:
        return {"status": "ok"}

    msg_type = data.get("type", "") or data.get("message", {}).get("type", "")
    call_data = data.get("call", data)

    call_id = call_data.get("id", "")
    transcript = call_data.get("transcript", "")
    summary = call_data.get("summary", "")
    ended_reason = call_data.get("endedReason", "")
    customer = call_data.get("customer", {})
    phone = customer.get("number", "") or call_data.get("to", "")
    lead_name = customer.get("name", "")

    logger.info("Vapi webhook: call_id=%s ended_reason=%s", call_id, ended_reason)

    full_text = (transcript + " " + summary).lower()

    # Detect outcome
    demo_booked = any(kw in full_text for kw in [
        "book", "demo", "schedule", "booking link", "confirmation", "email"
    ])
    is_interested = any(kw in full_text for kw in [
        "interested", "yes", "sure", "sounds good", "tell me more"
    ])
    not_interested = any(kw in full_text for kw in [
        "not interested", "no thanks", "don't need", "remove me"
    ])

    # Extract email from transcript
    email = extract_email_from_transcript(transcript)
    logger.info("Extracted email: '%s' | demo_booked: %s", email, demo_booked)

    # Update DB + send email
    if phone:
        async with async_session_factory() as session:
            lead = await db.find_lead_by_phone(session, phone)
            if lead:
                if demo_booked:
                    await db.update_lead_status(session, lead.id, LeadStatus.demo_scheduled)
                    notes = f"Demo booked via AI call. Email: {email}. Summary: {summary[:200]}"
                    await db.update_lead(session, lead.id, notes=notes)
                elif is_interested:
                    await db.update_lead_status(session, lead.id, LeadStatus.interested)
                elif not_interested:
                    await db.update_lead_status(session, lead.id, LeadStatus.not_interested)
                else:
                    await db.update_lead_status(session, lead.id, LeadStatus.contacted)

                await db.create_interaction_log(session, {
                    "lead_id": lead.id,
                    "agent_type": "cold_calling",
                    "channel": "call",
                    "direction": "outbound",
                    "summary": summary or f"Vapi AI call. Ended: {ended_reason}",
                    "outcome": "demo_booked" if demo_booked else (
                        "interested" if is_interested else "contacted"
                    ),
                    "raw_transcript": transcript,
                })
                await session.commit()

                # Send real booking email if demo booked and email found
                if demo_booked and email:
                    name = lead_name or f"{lead.first_name} {lead.last_name}".strip()
                    sent = await send_demo_booking_email(email, name)
                    logger.info("Booking email sent=%s to %s", sent, email)

    return {
        "status": "received",
        "call_id": call_id,
        "demo_booked": demo_booked,
        "email_found": email,
        "outcome": "demo_booked" if demo_booked else (
            "interested" if is_interested else "contacted"
        ),
    }


# ── Bland AI webhook (kept for compatibility) ─────────────────────────────────

@router.post("/call-webhook")
async def bland_call_webhook(request: Request):
    """Receives call outcome from Bland AI."""
    try:
        data = await request.json()
    except Exception:
        return {"status": "ok"}

    call_id = data.get("call_id", "")
    transcript = data.get("transcript", "")
    summary = data.get("summary", "")
    phone = data.get("to", "") or data.get("phone_number", "")
    lead_name = data.get("variables", {}).get("lead_name", "")

    logger.info("Bland webhook: call_id=%s", call_id)

    full_text = (transcript + " " + summary).lower()
    demo_booked = any(kw in full_text for kw in ["book", "demo", "schedule", "email"])
    is_interested = any(kw in full_text for kw in ["interested", "yes", "sure"])
    not_interested = any(kw in full_text for kw in ["not interested", "no thanks", "remove"])

    email = extract_email_from_transcript(transcript)

    if phone:
        async with async_session_factory() as session:
            lead = await db.find_lead_by_phone(session, phone)
            if lead:
                if demo_booked:
                    await db.update_lead_status(session, lead.id, LeadStatus.demo_scheduled)
                elif is_interested:
                    await db.update_lead_status(session, lead.id, LeadStatus.interested)
                elif not_interested:
                    await db.update_lead_status(session, lead.id, LeadStatus.not_interested)
                else:
                    await db.update_lead_status(session, lead.id, LeadStatus.contacted)

                await db.create_interaction_log(session, {
                    "lead_id": lead.id,
                    "agent_type": "cold_calling",
                    "channel": "call",
                    "direction": "outbound",
                    "summary": summary or "Bland AI call completed",
                    "outcome": "demo_booked" if demo_booked else "contacted",
                    "raw_transcript": transcript,
                })
                await session.commit()

                if demo_booked and email:
                    name = lead_name or f"{lead.first_name} {lead.last_name}".strip()
                    await send_demo_booking_email(email, name)

    return {"status": "received", "call_id": call_id, "demo_booked": demo_booked}


@router.get("/call-transcript/{call_id}")
async def get_call_transcript(call_id: str):
    """Get transcript from Vapi."""
    import httpx
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.environ.get("VAPI_API_KEY", "")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"https://api.vapi.ai/call/{call_id}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "call_id": call_id,
                "status": data.get("status"),
                "ended_reason": data.get("endedReason"),
                "transcript": data.get("transcript", ""),
                "summary": data.get("summary", ""),
                "cost": data.get("cost", 0),
            }
    return {"call_id": call_id, "error": "not found"}
