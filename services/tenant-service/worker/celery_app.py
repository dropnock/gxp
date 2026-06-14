from celery import Celery
from app.config import settings

celery_app = Celery(
    "gxp-tenant",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_url,
    include=["worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={"worker.tasks.*": {"queue": "tenant"}},
    worker_prefetch_multiplier=1,
    beat_schedule={
        "expire-cross-tenant-grants": {
            "task": "worker.tasks.expire_grants",
            "schedule": 300.0,  # every 5 minutes
        },
    },
)
