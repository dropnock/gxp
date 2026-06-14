"""
Celery tasks for workflow execution.

execute_workflow_step:
  Called after: instance creation, task completion, timer ticks.
  1. Load instance + definition from DB
  2. Deserialize workflow state
  3. Run engine steps (advancing automatic tasks)
  4. Sync task_instances rows for newly ready human tasks
  5. Serialize and persist updated state
  6. If workflow is complete, mark instance status='completed'
  7. Emit audit event

tick_timer_events:
  Beat task (every 60s).  Finds 'running' instances and re-runs engine
  steps so that intermediate timer events and boundary events fire.

Uses synchronous SQLAlchemy (psycopg2) — Celery runs in sync mode.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import create_engine, text

from app.config import settings
from app.engine import (
    complete_human_task as engine_complete_task,
    deserialize_workflow,
    get_variables,
    is_completed,
    run_engine_steps,
    serialize_workflow,
)
from worker.celery_app import celery_app

logger = logging.getLogger(__name__)

_SYNC_DB_URL = settings.database_url.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)
_engine = create_engine(_SYNC_DB_URL, pool_pre_ping=True)


def _emit(event_type: str, instance_id: str, tenant_slug: str, actor_id: str, outcome: str, meta: dict) -> None:
    from gxp_shared.audit.emitter import emit_audit_event
    try:
        asyncio.run(emit_audit_event(
            redis_url=settings.valkey_url,
            service="workflow-service",
            event_type=event_type,
            actor_id=actor_id,
            resource_type="workflow_instance",
            resource_id=instance_id,
            action=event_type,
            outcome=outcome,
            metadata={"tenant_slug": tenant_slug, **meta},
        ))
    except Exception as exc:  # noqa: BLE001
        logger.error("Audit emit failed: %s", exc)


def _sync_task_instances(conn, instance_id: str, tenant_slug: str, ready_tasks) -> None:
    """Upsert TaskInstance rows for all ready human tasks."""
    conn.execute(text(f'SET search_path TO "t_{tenant_slug}", public'))

    existing = conn.execute(
        text("SELECT spiff_task_id FROM task_instances WHERE instance_id = :iid AND status = 'ready'"),
        {"iid": instance_id},
    ).fetchall()
    existing_ids = {r.spiff_task_id for r in existing}

    for ht in ready_tasks:
        if ht.spiff_task_id in existing_ids:
            continue
        conn.execute(text("""
            INSERT INTO task_instances
                (id, instance_id, spiff_task_id, task_name, task_title,
                 form_schema, status, candidate_roles, created_at, completion_data)
            VALUES
                (:id, :iid, :spiff_id, :name, :title,
                 :form::jsonb, 'ready', :roles::jsonb, :now, '{}')
            ON CONFLICT (instance_id, spiff_task_id) DO NOTHING
        """), {
            "id": str(uuid4()),
            "iid": instance_id,
            "spiff_id": ht.spiff_task_id,
            "name": ht.task_name,
            "title": ht.task_title,
            "form": json.dumps(ht.form_schema),
            "roles": json.dumps(ht.candidate_roles),
            "now": datetime.now(tz=timezone.utc),
        })


@celery_app.task(name="worker.tasks.execute_workflow_step", bind=True, max_retries=3, default_retry_delay=30)
def execute_workflow_step(self, instance_id: str, tenant_slug: str, actor_id: str = "system") -> None:
    """Advance a workflow instance through all currently executable steps."""
    try:
        with _engine.begin() as conn:
            conn.execute(text(f'SET search_path TO "t_{tenant_slug}", public'))

            row = conn.execute(text("""
                SELECT wi.state_json, wi.definition_id, wi.status,
                       wd.xml_content, wd.definition_type
                FROM workflow_instances wi
                JOIN workflow_definitions wd ON wd.id = wi.definition_id
                WHERE wi.id = :iid
            """), {"iid": instance_id}).fetchone()

            if not row:
                logger.error("Instance %s not found", instance_id)
                return
            if row.status in ("completed", "cancelled"):
                return

            # Deserialize and run engine steps
            workflow = deserialize_workflow(row.state_json)
            ready_tasks = run_engine_steps(workflow)

            completed = is_completed(workflow)
            new_status = "completed" if completed else "waiting" if not ready_tasks else "running"
            variables = get_variables(workflow)

            # Persist updated state
            conn.execute(text("""
                UPDATE workflow_instances
                SET state_json = :state::jsonb,
                    variables  = :vars::jsonb,
                    status     = :status,
                    updated_at = :now,
                    completed_at = CASE WHEN :completed THEN :now ELSE completed_at END
                WHERE id = :iid
            """), {
                "state": json.dumps(serialize_workflow(workflow)),
                "vars": json.dumps(variables),
                "status": new_status,
                "now": datetime.now(tz=timezone.utc),
                "completed": completed,
                "iid": instance_id,
            })

            if ready_tasks:
                _sync_task_instances(conn, instance_id, tenant_slug, ready_tasks)

        outcome = "completed" if completed else "success"
        _emit("workflow.step_executed", instance_id, tenant_slug, actor_id, outcome,
              {"new_status": new_status, "ready_tasks": len(ready_tasks)})

    except Exception as exc:
        logger.error("execute_workflow_step failed for %s: %s", instance_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(name="worker.tasks.complete_task", bind=True, max_retries=3, default_retry_delay=30)
def complete_task(
    self,
    task_instance_id: str,
    instance_id: str,
    spiff_task_id: str,
    tenant_slug: str,
    completion_data: dict,
    actor_id: str,
) -> None:
    """Complete a human task and advance the workflow."""
    try:
        with _engine.begin() as conn:
            conn.execute(text(f'SET search_path TO "t_{tenant_slug}", public'))

            row = conn.execute(text("""
                SELECT wi.state_json, wd.xml_content
                FROM workflow_instances wi
                JOIN workflow_definitions wd ON wd.id = wi.definition_id
                WHERE wi.id = :iid
            """), {"iid": instance_id}).fetchone()

            if not row:
                raise ValueError(f"Instance {instance_id} not found")

            workflow = deserialize_workflow(row.state_json)
            ready_tasks = engine_complete_task(workflow, spiff_task_id, completion_data)

            completed = is_completed(workflow)
            new_status = "completed" if completed else "waiting" if not ready_tasks else "running"
            now = datetime.now(tz=timezone.utc)

            conn.execute(text("""
                UPDATE task_instances
                SET status = 'completed', completed_at = :now,
                    completion_data = :data::jsonb
                WHERE id = :tid
            """), {"now": now, "data": json.dumps(completion_data), "tid": task_instance_id})

            conn.execute(text("""
                UPDATE workflow_instances
                SET state_json = :state::jsonb,
                    variables  = :vars::jsonb,
                    status     = :status,
                    updated_at = :now,
                    completed_at = CASE WHEN :completed THEN :now ELSE completed_at END
                WHERE id = :iid
            """), {
                "state": json.dumps(serialize_workflow(workflow)),
                "vars": json.dumps(get_variables(workflow)),
                "status": new_status,
                "now": now,
                "completed": completed,
                "iid": instance_id,
            })

            if ready_tasks:
                _sync_task_instances(conn, instance_id, tenant_slug, ready_tasks)

        _emit("workflow.task_completed", instance_id, tenant_slug, actor_id, "success",
              {"task_instance_id": task_instance_id, "spiff_task_id": spiff_task_id})

    except Exception as exc:
        logger.error("complete_task failed for %s/%s: %s", instance_id, spiff_task_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(name="worker.tasks.tick_timer_events")
def tick_timer_events() -> None:
    """
    Beat task: advance all running workflow instances so timer/boundary events fire.
    Dispatches individual execute_workflow_step tasks to avoid blocking the beat process.
    """
    with _engine.connect() as conn:
        # This query runs across all tenant schemas — we need to query per-schema.
        # The migrate_tenants script keeps a list of active slugs in Valkey;
        # here we read it synchronously via redis-py.
        import redis
        r = redis.from_url(settings.valkey_url)
        slugs = [s.decode() if isinstance(s, bytes) else s
                 for s in r.smembers("gxp:tenants:active")]

        for slug in slugs:
            try:
                conn.execute(text(f'SET search_path TO "t_{slug}", public'))
                rows = conn.execute(text(
                    "SELECT id FROM workflow_instances WHERE status = 'running'"
                )).fetchall()
                for row in rows:
                    execute_workflow_step.apply_async(
                        args=[str(row.id), slug, "timer"],
                        queue="workflow",
                    )
            except Exception as exc:  # noqa: BLE001
                logger.error("Timer tick failed for tenant %s: %s", slug, exc)
