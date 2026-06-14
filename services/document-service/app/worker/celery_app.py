"""
Celery application for the document service.

The worker runs as a separate process (document-worker in docker-compose).
Tasks use synchronous SQLAlchemy (psycopg2) since Celery workers are sync
— the async session from the FastAPI app is not available in the worker.
"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "document-worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={"app.worker.tasks.*": {"queue": "document"}},
    worker_prefetch_multiplier=1,  # one task at a time per worker — AV scans are CPU-bound
)
