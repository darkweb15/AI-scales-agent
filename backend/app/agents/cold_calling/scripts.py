"""Call script loader.

Scripts are keyed by name and can be parameterised with lead data.
In production these would be loaded from a database or config file.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

_SCRIPTS: Dict[str, str] = {
    "cold_call": (
        "Hi {first_name}, this is an AI assistant calling on behalf of our sales team. "
        "I wanted to reach out about how we can help {company} with our solution. "
        "Do you have a moment to chat?"
    ),
    "voicemail": (
        "Hi {first_name}, this is a message for you from our sales team. "
        "We'd love to connect about how we can help {company}. "
        "Please call us back at your convenience. Thank you!"
    ),
}


def load_script(name: str, lead: Optional[Any] = None) -> str:
    """Return the script for *name*, optionally formatted with *lead* data.

    Parameters
    ----------
    name:
        Script key (e.g. ``'cold_call'``, ``'voicemail'``).
    lead:
        Lead object whose attributes are used to format the template.
        If None, the raw template string is returned.
    """
    template = _SCRIPTS.get(name, "")
    if lead is None:
        return template

    try:
        return template.format(
            first_name=getattr(lead, "first_name", ""),
            last_name=getattr(lead, "last_name", ""),
            company=getattr(lead, "company", "your company"),
        )
    except (KeyError, AttributeError):
        return template
