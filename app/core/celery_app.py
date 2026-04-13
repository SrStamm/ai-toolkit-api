"""
Celery application configuration with Redis as broker and result backend.
"""

from celery import Celery
from .settings import get_settings


settings = get_settings()

# Get Redis URL from settings
redis_url = (
    settings.redis_url
    or f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
)

celery_app = Celery(
    "ai_toolkit",
    broker=redis_url,
    result_backend=redis_url,  # Store task results in Redis
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Configure task result expiration (1 hour default)
celery_app.conf.result_expires = 3600

celery_app.autodiscover_tasks(["app.api.rag.jobs.celery_tasks"])
