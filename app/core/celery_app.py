import os
from celery import Celery

redis_url = os.getenv("REDIS_URL")

celery_app = Celery(
    "ai_toolkit",
    broker=redis_url,
    # backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.autodiscover_tasks(["app.features.rag.jobs.celery_tasks"])
