from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "gxp-audit",
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
    task_routes={"worker.tasks.*": {"queue": "audit"}},
    worker_prefetch_multiplier=1,
    beat_schedule={
        # First day of every month at 01:00 UTC — create next month's partition
        "create-next-partition": {
            "task": "worker.tasks.create_next_partition",
            "schedule": crontab(day_of_month="1", hour="1", minute="0"),
        },
        # First day of every month at 02:00 UTC — archive and drop old partitions
        "archive-old-partitions": {
            "task": "worker.tasks.archive_old_partitions",
            "schedule": crontab(day_of_month="1", hour="2", minute="0"),
        },
    },
)
