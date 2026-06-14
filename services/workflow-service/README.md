# services/workflow-service

Stores and executes BPMN 2.0 workflow definitions and DMN 1.3 decision tables. It is the engine behind GXP's approval workflows and automated decision rules. Users design processes in the portal's bpmn-js / dmn-js editors; this service validates, stores, and executes them using SpiffWorkflow.

See [ADR-002](../../docs/adr/ADR-002-spiffworkflow-for-bpmn-and-dmn-execution.md) for the engine selection rationale.

---

## Key Design Decisions

- **SpiffWorkflow as BPMN/DMN engine** — chosen because it is pure Python, LGPL-2.1 (used as a dynamic library so the license does not propagate to GXP), air-gap compatible, and serialises full workflow state to JSON for DB storage. See ADR-002.
- **Synchronous engine, asynchronous API** — the SpiffWorkflow engine is synchronous (no async I/O). All engine calls run inside Celery tasks (`workflow` queue), never in the FastAPI async path. The API creates the instance and enqueues a Celery task; the client polls `GET /instances/{id}` to observe status changes.
- **State serialised to JSON** — `WorkflowInstance.state_json` stores the full `BpmnWorkflow` state between engine steps (via `BpmnWorkflowSerializer`). This makes instances restartable after a worker crash and allows the DB to be the authoritative state store.
- **Soft-delete for definitions** — `WorkflowDefinition.is_active = False` rather than hard delete, because running instances reference their definition version. History is preserved.
- **Three-stage BPMN validation** — upload triggers: (1) lxml well-formedness check, (2) presence of a `<process>` element, (3) SpiffWorkflow parse. All three must pass before the definition is stored.

---

## Structure

```
services/workflow-service/
├── app/
│   ├── api/v1/
│   │   ├── definitions.py       # BPMN definition CRUD
│   │   ├── dmn_definitions.py   # DMN definition CRUD + evaluate endpoint
│   │   ├── instances.py         # Instance lifecycle (start, list, get, cancel)
│   │   └── tasks.py             # Human task inbox, claim, complete
│   ├── config.py
│   ├── db/
│   │   ├── session.py
│   │   └── migrations/versions/001_create_workflow_tables.py
│   ├── engine/
│   │   └── runner.py            # SpiffWorkflow integration (validate, create, run, serialize)
│   └── models/workflow.py       # WorkflowDefinition, WorkflowInstance, TaskInstance ORM models
├── worker/
│   ├── celery_app.py
│   └── tasks.py                 # execute_workflow_step, complete_task Celery tasks
└── tests/
    └── test_runner.py
```

---

## Dependencies / Licenses

| Package | License | Purpose |
|---|---|---|
| fastapi 0.115 | MIT | API framework |
| uvicorn 0.32 | BSD-3 | ASGI server |
| sqlalchemy 2 async | MIT | ORM |
| asyncpg 0.30 | Apache 2.0 | PostgreSQL driver |
| alembic 1.14 | MIT | Migrations |
| SpiffWorkflow | LGPL-2.1 | BPMN/DMN execution engine |
| lxml | BSD-3 | BPMN/DMN XML parsing and validation |
| celery 5.4 | BSD-3 | Async task queue |
| redis 5.2 | MIT | Celery broker (Valkey DB 1) |
| gxp-shared | internal | Auth, audit middleware |

---

## Local Development

```bash
uv sync
cd services/workflow-service
uvicorn app.main:app --reload --port 8002

# Start Celery worker (separate terminal)
celery -A worker.celery_app worker --loglevel=info -Q workflow
```

Run tests:
```bash
uv run pytest services/workflow-service/tests/ -q
```

---

## REST API

Base path: `/api/v1/workflow`

### BPMN Definitions

| Method | Path | Required Role | Description |
|---|---|---|---|
| `POST` | `/workflow/definitions` | `gxp-developer`, `gxp-admin` | Create definition (validates BPMN XML) |
| `GET` | `/workflow/definitions` | `gxp-developer`, `gxp-admin` | List definitions |
| `GET` | `/workflow/definitions/{id}` | `gxp-developer`, `gxp-admin` | Get definition with XML |
| `PUT` | `/workflow/definitions/{id}` | `gxp-developer`, `gxp-admin` | Update (re-validates, increments version) |
| `DELETE` | `/workflow/definitions/{id}` | `gxp-admin` | Soft-delete |

### DMN Definitions

Same pattern under `/workflow/dmn-definitions`, plus:

| Method | Path | Description |
|---|---|---|
| `POST` | `/workflow/dmn-definitions/{id}/evaluate` | Evaluate a DMN decision table with input variables |

### Instances

| Method | Path | Required Role | Description |
|---|---|---|---|
| `POST` | `/workflow/instances` | any user role | Start a new instance (202 Accepted, async) |
| `GET` | `/workflow/instances` | any user role | List instances (filter by status, definition) |
| `GET` | `/workflow/instances/{id}` | any user role | Get instance + task list |
| `POST` | `/workflow/instances/{id}/cancel` | `gxp-admin` | Cancel a running instance |

### Tasks (Human task inbox)

| Method | Path | Required Role | Description |
|---|---|---|---|
| `GET` | `/workflow/tasks/inbox` | any user role | Tasks assigned to me or matching my roles |
| `GET` | `/workflow/tasks/{id}` | any user role | Task detail with form schema |
| `POST` | `/workflow/tasks/{id}/claim` | any user role | Assign task to self |
| `POST` | `/workflow/tasks/{id}/complete` | any user role | Submit form data, advance workflow (async) |

---

## Configuration

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Workflow-service database (`gxp_workflow`) |
| `VALKEY_URL` | Valkey (tenant cache, DB 1) |
| `CELERY_BROKER_URL` | Valkey (Celery broker, DB 1) |
| `CLIENT_ID` / `CLIENT_SECRET` | Service OAuth2 credentials |

---

## Engine Notes

`app/engine/runner.py` contains all SpiffWorkflow integration logic:

- `validate_bpmn(xml)` — three-stage validation, returns `(bool, error_str)`
- `create_workflow(bpmn_xml, process_id, initial_variables, dmn_xml_list)` — parse and build a `BpmnWorkflow`
- `run_engine_steps(workflow)` — call `do_engine_steps()` and return any newly READY `HumanTask` objects
- `complete_human_task(workflow, spiff_task_id, completion_data)` — inject form data, complete task, advance engine
- `serialize_workflow(workflow)` / `deserialize_workflow(state_dict)` — JSON round-trip via `BpmnWorkflowSerializer`

Celery tasks call these synchronously inside a regular (non-async) function, then persist the updated `state_json` back to the DB.
