"""Celery application instance.

Import this module to get the configured Celery app. The broker and backend
URLs are read from the REDIS_URL environment variable (defaulting to
redis://localhost:6379/0).
"""

import os

from celery import Celery

from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "ai_sales",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.app.core.task_queue"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
