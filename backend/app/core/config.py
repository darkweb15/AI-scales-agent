"""Config dataclass loaded from environment variables via python-dotenv."""

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def _env_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    return int(val) if val is not None else default


def _env_float(key: str, default: float) -> float:
    val = os.environ.get(key)
    return float(val) if val is not None else default


def _env_str(key: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(key, default)


def _env_str_required(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise ValueError(f"Required environment variable '{key}' is not set.")
    return val


@dataclass
class Config:
    """All system configuration loaded from environment variables.

    Defaults match the spec. Required fields (database_url, hmac_secret)
    raise ValueError if missing.
    """

    # Orchestrator
    orchestrator_poll_interval_seconds: int = field(
        default_factory=lambda: _env_int("ORCHESTRATOR_POLL_INTERVAL_SECONDS", 30)
    )

    # Cooldown / attempt limits
    cooldown_minutes: int = field(
        default_factory=lambda: _env_int("COOLDOWN_MINUTES", 60)
    )
    max_cold_call_attempts: int = field(
        default_factory=lambda: _env_int("MAX_COLD_CALL_ATTEMPTS", 3)
    )
    max_total_follow_up_attempts: int = field(
        default_factory=lambda: _env_int("MAX_TOTAL_FOLLOW_UP_ATTEMPTS", 5)
    )
    max_task_retries: int = field(
        default_factory=lambda: _env_int("MAX_TASK_RETRIES", 3)
    )

    # Scheduling
    follow_up_delay_hours: int = field(
        default_factory=lambda: _env_int("FOLLOW_UP_DELAY_HOURS", 24)
    )
    scheduling_window_days: int = field(
        default_factory=lambda: _env_int("SCHEDULING_WINDOW_DAYS", 14)
    )
    max_slots_to_offer: int = field(
        default_factory=lambda: _env_int("MAX_SLOTS_TO_OFFER", 3)
    )
    demo_duration_minutes: int = field(
        default_factory=lambda: _env_int("DEMO_DURATION_MINUTES", 30)
    )

    # AI thresholds
    auto_reply_confidence_threshold: float = field(
        default_factory=lambda: _env_float("AUTO_REPLY_CONFIDENCE_THRESHOLD", 0.75)
    )

    # Infrastructure
    database_url: str = field(
        default_factory=lambda: _env_str_required("DATABASE_URL")
    )
    redis_url: str = field(
        default_factory=lambda: _env_str("REDIS_URL", "redis://localhost:6379/0")
    )

    # Integrations
    slack_webhook_url: Optional[str] = field(
        default_factory=lambda: _env_str("SLACK_WEBHOOK_URL")
    )
    hmac_secret: str = field(
        default_factory=lambda: _env_str_required("HMAC_SECRET")
    )

    # Calling hours (24h, local to lead timezone)
    calling_hours_start: int = field(
        default_factory=lambda: _env_int("CALLING_HOURS_START", 9)
    )
    calling_hours_end: int = field(
        default_factory=lambda: _env_int("CALLING_HOURS_END", 17)
    )


# Module-level singleton — lazily instantiated so tests can patch env vars first.
_config: Optional[Config] = None


def get_config() -> Config:
    """Return the module-level Config singleton, creating it on first call."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config() -> None:
    """Reset the singleton (useful in tests that patch environment variables)."""
    global _config
    _config = None
