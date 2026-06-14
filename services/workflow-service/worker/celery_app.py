from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "gxp-workflow",
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
    task_routes={"worker.tasks.*": {"queue": "workflow"}},
    worker_prefetch_multiplier=1,
    # Beat schedule: tick timer events every 60 seconds
    beat_schedule={
        "tick-workflow-timers": {
            "task": "worker.tasks.tick_timer_events",
            "schedule": 60.0,
        },
    },
)
