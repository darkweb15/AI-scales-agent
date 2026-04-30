"""Test endpoint — Human-like AI voice calls.

Supported providers (in order of voice quality):
  1. vapi    — Vapi.ai + ElevenLabs Rachel voice (best, most human)
  2. bland   — Bland AI + Maya voice (great Indian female voice)
  3. elevenlabs — ElevenLabs + Twilio webhook (full control)
  4. twilio  — Twilio + Polly.Aditi (free, decent Indian voice)
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.base import get_session
from app.database.service import DatabaseService
import uuid, os
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()
db = DatabaseService()


class CallRequest(BaseModel):
    to_number: str
    lead_id: str = ""
    provider: str = "vapi"  # "vapi", "bland", "elevenlabs", "twilio"


@router.post("/test-call")
async def make_test_call(body: CallRequest, session: AsyncSession = Depends(get_session)):
    """Trigger a real human-voice AI call."""

    # Get lead details for personalization
    lead_name = ""
    company = ""
    if body.lead_id:
        try:
            lead = await db.get_lead(session, uuid.UUID(body.lead_id))
            if lead:
                lead_name = f"{lead.first_name} {lead.last_name}".strip()
                company = lead.company or ""
        except Exception:
            pass

    try:
        if body.provider == "bland":
            # Bland AI — ultra-realistic Indian female voice "Maya"
            from app.agents.cold_calling.bland_telephony import BlandAITelephonyAPI
            telephony = BlandAITelephonyAPI()
            if not telephony._api_key:
                return {
                    "success": False,
                    "error": "BLAND_AI_API_KEY not set in .env — get free key at app.bland.ai",
                }
            session_obj = telephony.initiate_call(body.to_number, lead_name, company)
            provider_name = "Bland AI (Maya — Indian female voice)"
            voice_info = "Ultra-realistic Indian female voice, natural pauses, sounds 100% human"

        elif body.provider == "elevenlabs":
            # ElevenLabs + Twilio webhook — full real-time conversation
            from app.agents.cold_calling.elevenlabs_twilio import ElevenLabsTwilioAgent
            telephony = ElevenLabsTwilioAgent()
            if not telephony._twilio_sid:
                return {
                    "success": False,
                    "error": "TWILIO_ACCOUNT_SID not set in .env",
                }
            if not telephony._el_key:
                return {
                    "success": False,
                    "error": "ELEVENLABS_API_KEY not set in .env — get free key at elevenlabs.io",
                }
            session_obj = telephony.initiate_call(body.to_number)
            provider_name = "ElevenLabs + Twilio (Rachel voice)"
            voice_info = "ElevenLabs Rachel voice with Groq AI brain — real-time conversation"

        elif body.provider == "twilio":
            # Twilio + Polly.Aditi — free Indian voice (no extra API key needed)
            from app.agents.cold_calling.twilio_telephony import TwilioTelephonyAPI
            telephony = TwilioTelephonyAPI()
            if not telephony._sid:
                return {
                    "success": False,
                    "error": "TWILIO_ACCOUNT_SID not set in .env",
                }
            session_obj = telephony.initiate_call(body.to_number)
            provider_name = "Twilio + Polly.Aditi (Indian female)"
            voice_info = "Amazon Polly Aditi — Indian English female voice, free with Twilio"

        else:
            # Default: Vapi.ai — best quality, ElevenLabs Rachel voice
            from app.agents.cold_calling.vapi_telephony import VapiTelephonyAPI
            telephony = VapiTelephonyAPI()
            if not telephony._api_key:
                return {
                    "success": False,
                    "error": "VAPI_API_KEY not set in .env — get free key at vapi.ai",
                }
            session_obj = telephony.initiate_call(body.to_number, lead_name, company)
            provider_name = "Vapi.ai (ElevenLabs Rachel voice)"
            voice_info = "ElevenLabs Rachel voice + Groq LLaMA brain — most human-sounding"

        return {
            "success": True,
            "call_id": session_obj.call_id,
            "status": session_obj.status,
            "to": body.to_number,
            "lead_name": lead_name or "Unknown",
            "provider": provider_name,
            "voice_info": voice_info,
            "message": f"🎙️ Priya (AI) is calling {lead_name or body.to_number}! {voice_info}.",
        }

    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.get("/call-status/{call_id}")
async def get_call_status(call_id: str, provider: str = "vapi"):
    """Get call status and transcript."""
    try:
        if provider == "bland":
            from app.agents.cold_calling.bland_telephony import BlandAITelephonyAPI
            telephony = BlandAITelephonyAPI()
            data = telephony.get_call_status(call_id)
            return {
                "call_id": call_id,
                "provider": "bland",
                "status": data.get("status", "unknown"),
                "duration": data.get("call_length", 0),
                "transcript": telephony.get_transcript(call_id),
                "summary": data.get("summary", ""),
            }
        else:
            from app.agents.cold_calling.vapi_telephony import VapiTelephonyAPI
            telephony = VapiTelephonyAPI()
            data = telephony.get_call_details(call_id)
            return {
                "call_id": call_id,
                "provider": "vapi",
                "status": data.get("status", "unknown"),
                "duration": data.get("endedAt", ""),
                "transcript": telephony.get_transcript(call_id),
                "summary": data.get("summary", ""),
                "cost": data.get("cost", 0),
            }
    except Exception as exc:
        return {"call_id": call_id, "error": str(exc)}


@router.get("/voice-providers")
async def list_voice_providers():
    """List available voice providers and their status."""
    providers = []

    # Check Vapi
    vapi_key = os.environ.get("VAPI_API_KEY", "")
    providers.append({
        "id": "vapi",
        "name": "Vapi.ai",
        "voice": "ElevenLabs Rachel (American female)",
        "quality": "⭐⭐⭐⭐⭐ Most human-sounding",
        "cost": "$0.05/min",
        "configured": bool(vapi_key),
        "recommended": True,
    })

    # Check Bland AI
    bland_key = os.environ.get("BLAND_AI_API_KEY", "")
    providers.append({
        "id": "bland",
        "name": "Bland AI",
        "voice": "Maya (Indian female)",
        "quality": "⭐⭐⭐⭐⭐ Ultra-realistic Indian voice",
        "cost": "$0.09/min",
        "configured": bool(bland_key),
        "recommended": True,
    })

    # Check ElevenLabs
    el_key = os.environ.get("ELEVENLABS_API_KEY", "")
    twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    providers.append({
        "id": "elevenlabs",
        "name": "ElevenLabs + Twilio",
        "voice": "Rachel / Bella / Josh (multiple options)",
        "quality": "⭐⭐⭐⭐ Ultra-realistic, full control",
        "cost": "$0.30/1000 chars + Twilio",
        "configured": bool(el_key and twilio_sid),
        "recommended": False,
    })

    # Check Twilio
    providers.append({
        "id": "twilio",
        "name": "Twilio + Polly.Aditi",
        "voice": "Aditi (Indian English female)",
        "quality": "⭐⭐⭐ Good Indian accent, free",
        "cost": "Included with Twilio",
        "configured": bool(twilio_sid),
        "recommended": False,
    })

    return {"providers": providers}
