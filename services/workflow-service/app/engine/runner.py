"""
SpiffWorkflow engine integration.

Responsibilities:
- Parse BPMN (and associated DMN) XML into a BpmnWorkflow
- Execute automatic engine steps (script tasks, gateways, service tasks)
- Enumerate ready human tasks and return them as TaskInstance data
- Serialize/deserialize workflow state to/from JSON (stored in DB)

All operations are synchronous — this module is called from Celery tasks
which run in a sync context.  FastAPI routes call into this via asyncio.run()
when needed, but the engine itself has no async code.

SpiffWorkflow >= 3.0 API notes:
  - BpmnParser.add_bpmn_str() / add_dmn_str() load XML into the parser
  - parser.get_spec(process_id) returns the top-level WorkflowSpec
  - BpmnWorkflow(spec, subprocesses) creates a new instance
  - workflow.do_engine_steps() advances through automatic tasks
  - workflow.get_tasks(TaskState.READY) returns ready human tasks
  - BpmnWorkflowSerializer serializes/deserializes full state as JSON
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from lxml import etree
from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnParser
from SpiffWorkflow.bpmn.serializer.workflow import BpmnWorkflowSerializer
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.task import TaskState

logger = logging.getLogger(__name__)

# Singleton serializer (thread-safe, stateless)
_serializer = BpmnWorkflowSerializer()


@dataclass
class HumanTask:
    """Flattened representation of a BPMN UserTask ready for DB persistence."""
    spiff_task_id: str
    task_name: str
    task_title: str
    form_schema: dict = field(default_factory=dict)
    candidate_roles: list[str] = field(default_factory=list)


def sha256_xml(xml: str) -> str:
    return hashlib.sha256(xml.encode()).hexdigest()


def extract_process_id(bpmn_xml: str) -> str | None:
    """Return the id attribute of the first <process> element in the BPMN."""
    try:
        root = etree.fromstring(bpmn_xml.encode())
        # BPMN 2.0 namespace
        ns = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL"}
        processes = root.findall(".//bpmn:process", ns)
        if not processes:
            # Try without namespace (some exporters omit it)
            processes = root.findall(".//{*}process")
        return processes[0].get("id") if processes else None
    except Exception:
        return None


def extract_dmn_id(dmn_xml: str) -> str | None:
    """Return the id attribute of the first <decision> element in the DMN."""
    try:
        root = etree.fromstring(dmn_xml.encode())
        decisions = root.findall(".//{*}decision")
        return decisions[0].get("id") if decisions else None
    except Exception:
        return None


def validate_bpmn(bpmn_xml: str) -> tuple[bool, str]:
    """
    Validate BPMN XML:
    1. Well-formed XML (lxml parse)
    2. Contains at least one <process> element
    3. Parseable by SpiffWorkflow (catches semantic errors)

    Returns (is_valid, error_message).
    """
    try:
        etree.fromstring(bpmn_xml.encode())
    except etree.XMLSyntaxError as e:
        return False, f"XML syntax error: {e}"

    process_id = extract_process_id(bpmn_xml)
    if not process_id:
        return False, "No <process> element found in BPMN"

    try:
        parser = BpmnParser()
        parser.add_bpmn_str(bpmn_xml)
        parser.get_spec(process_id)
    except Exception as e:
        return False, f"SpiffWorkflow parse error: {e}"

    return True, ""


def validate_dmn(dmn_xml: str) -> tuple[bool, str]:
    """Validate DMN XML: well-formed + contains at least one <decision>."""
    try:
        etree.fromstring(dmn_xml.encode())
    except etree.XMLSyntaxError as e:
        return False, f"XML syntax error: {e}"

    if not extract_dmn_id(dmn_xml):
        return False, "No <decision> element found in DMN"

    return True, ""


def create_workflow(
    bpmn_xml: str,
    process_id: str,
    initial_variables: dict[str, Any] | None = None,
    dmn_xml_list: list[str] | None = None,
) -> BpmnWorkflow:
    """Parse BPMN (+ optional DMN files) and return a fresh BpmnWorkflow."""
    parser = BpmnParser()
    parser.add_bpmn_str(bpmn_xml)
    for dmn_xml in (dmn_xml_list or []):
        parser.add_dmn_str(dmn_xml)

    spec = parser.get_spec(process_id)
    subprocesses = parser.get_subprocess_specs(process_id)
    workflow = BpmnWorkflow(spec, subprocesses)

    if initial_variables:
        workflow.data.update(initial_variables)

    return workflow


def run_engine_steps(workflow: BpmnWorkflow) -> list[HumanTask]:
    """
    Advance the workflow through all automatic tasks, then return any
    newly READY human tasks.  Calls do_engine_steps() in a loop until
    no more progress can be made automatically.
    """
    try:
        workflow.do_engine_steps()
    except Exception as e:
        logger.error("Engine step error: %s", e)
        raise

    return _collect_ready_tasks(workflow)


def _collect_ready_tasks(workflow: BpmnWorkflow) -> list[HumanTask]:
    ready = workflow.get_tasks(state=TaskState.READY)
    tasks = []
    for t in ready:
        task_spec = t.task_spec

        # Extract form schema from SpiffWorkflow extensions if present
        form_schema: dict = {}
        candidate_roles: list[str] = []
        if hasattr(task_spec, "form"):
            form_schema = _spiff_form_to_json_schema(task_spec.form)
        if hasattr(task_spec, "lane"):
            candidate_roles = [task_spec.lane] if task_spec.lane else []

        tasks.append(HumanTask(
            spiff_task_id=str(t.id),
            task_name=task_spec.name,
            task_title=getattr(task_spec, "documentation", None) or task_spec.name,
            form_schema=form_schema,
            candidate_roles=candidate_roles,
        ))
    return tasks


def complete_human_task(
    workflow: BpmnWorkflow,
    spiff_task_id: str,
    completion_data: dict[str, Any],
) -> list[HumanTask]:
    """
    Complete a UserTask by ID, inject form data into the workflow context,
    then advance engine steps.  Returns any newly ready human tasks.
    """
    task_uuid = UUID(spiff_task_id)
    task = workflow.get_task_from_id(task_uuid)
    if task is None:
        raise ValueError(f"Task {spiff_task_id} not found in workflow")
    if task.state != TaskState.READY:
        raise ValueError(f"Task {spiff_task_id} is not in READY state (state={task.state})")

    task.set_data(**completion_data)
    workflow.complete_task_from_id(task_uuid)
    return run_engine_steps(workflow)


def serialize_workflow(workflow: BpmnWorkflow) -> dict:
    """Serialize workflow state to a JSON-compatible dict for DB storage."""
    json_str = _serializer.serialize_json(workflow)
    return json.loads(json_str)


def deserialize_workflow(state_dict: dict) -> BpmnWorkflow:
    """Restore a BpmnWorkflow from its serialized state dict."""
    return _serializer.deserialize_json(json.dumps(state_dict))


def is_completed(workflow: BpmnWorkflow) -> bool:
    return workflow.is_completed()


def get_variables(workflow: BpmnWorkflow) -> dict[str, Any]:
    """Return top-level process variables for audit/query storage."""
    return dict(workflow.data)


def _spiff_form_to_json_schema(form) -> dict:
    """Convert a SpiffWorkflow CamundaFormData object to a JSON Schema dict."""
    if not form or not hasattr(form, "fields"):
        return {}
    properties: dict = {}
    required: list = []
    for f in form.fields:
        field_schema: dict = {"title": getattr(f, "label", f.id)}
        ftype = getattr(f, "type", "string")
        if ftype in ("long", "int"):
            field_schema["type"] = "integer"
        elif ftype == "boolean":
            field_schema["type"] = "boolean"
        elif ftype == "date":
            field_schema["type"] = "string"
            field_schema["format"] = "date"
        else:
            field_schema["type"] = "string"
        properties[f.id] = field_schema
        if getattr(f, "validation", None):
            for v in f.validation:
                if getattr(v, "name", None) == "required":
                    required.append(f.id)
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema
