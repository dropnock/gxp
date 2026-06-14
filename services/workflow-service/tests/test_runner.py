"""Tests for the SpiffWorkflow engine integration."""
from __future__ import annotations

import pytest

from app.engine.runner import (
    create_workflow,
    deserialize_workflow,
    extract_dmn_id,
    extract_process_id,
    is_completed,
    run_engine_steps,
    serialize_workflow,
    sha256_xml,
    validate_bpmn,
    validate_dmn,
)


# ── Minimal fixtures ──────────────────────────────────────────────────────────

VALID_BPMN = """\
<?xml version="1.0"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
             targetNamespace="http://gxp.internal">
  <process id="TestProcess" isExecutable="true">
    <startEvent id="start"/>
    <sequenceFlow id="flow1" sourceRef="start" targetRef="end"/>
    <endEvent id="end"/>
  </process>
</definitions>
"""

BPMN_WITH_USER_TASK = """\
<?xml version="1.0"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL"
             xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
             targetNamespace="http://gxp.internal">
  <process id="ReviewProcess" isExecutable="true">
    <startEvent id="start"/>
    <sequenceFlow id="f1" sourceRef="start" targetRef="review"/>
    <userTask id="review" name="Review Document"/>
    <sequenceFlow id="f2" sourceRef="review" targetRef="end"/>
    <endEvent id="end"/>
  </process>
</definitions>
"""

INVALID_XML = "this is not xml <at all>"

BPMN_NO_PROCESS = """\
<?xml version="1.0"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL">
</definitions>
"""

VALID_DMN = """\
<?xml version="1.0"?>
<definitions xmlns="https://www.omg.org/spec/DMN/20191111/MODEL/" id="defs">
  <decision id="ApprovalDecision" name="Approval">
    <decisionTable id="dt1" hitPolicy="FIRST">
      <input id="in1">
        <inputExpression typeRef="string"><text>status</text></inputExpression>
      </input>
      <output id="out1" typeRef="string" name="result"/>
      <rule id="r1">
        <inputEntry id="ie1"><text>"pending"</text></inputEntry>
        <outputEntry id="oe1"><text>"approve"</text></outputEntry>
      </rule>
    </decisionTable>
  </decision>
</definitions>
"""


# ── sha256_xml ────────────────────────────────────────────────────────────────

def test_sha256_xml_is_deterministic():
    h1 = sha256_xml(VALID_BPMN)
    h2 = sha256_xml(VALID_BPMN)
    assert h1 == h2
    assert len(h1) == 64


def test_sha256_xml_differs_for_different_content():
    assert sha256_xml(VALID_BPMN) != sha256_xml(BPMN_WITH_USER_TASK)


# ── extract_process_id ────────────────────────────────────────────────────────

def test_extract_process_id_valid():
    assert extract_process_id(VALID_BPMN) == "TestProcess"


def test_extract_process_id_no_process():
    assert extract_process_id(BPMN_NO_PROCESS) is None


def test_extract_process_id_invalid_xml():
    assert extract_process_id(INVALID_XML) is None


# ── extract_dmn_id ────────────────────────────────────────────────────────────

def test_extract_dmn_id_valid():
    assert extract_dmn_id(VALID_DMN) == "ApprovalDecision"


def test_extract_dmn_id_no_decision():
    assert extract_dmn_id("<definitions/>") is None


# ── validate_bpmn ─────────────────────────────────────────────────────────────

def test_validate_bpmn_valid():
    ok, err = validate_bpmn(VALID_BPMN)
    assert ok is True
    assert err == ""


def test_validate_bpmn_invalid_xml():
    ok, err = validate_bpmn(INVALID_XML)
    assert ok is False
    assert "syntax" in err.lower() or "xml" in err.lower()


def test_validate_bpmn_no_process():
    ok, err = validate_bpmn(BPMN_NO_PROCESS)
    assert ok is False
    assert "process" in err.lower()


def test_validate_bpmn_with_user_task():
    ok, err = validate_bpmn(BPMN_WITH_USER_TASK)
    assert ok is True


# ── validate_dmn ──────────────────────────────────────────────────────────────

def test_validate_dmn_valid():
    ok, err = validate_dmn(VALID_DMN)
    assert ok is True


def test_validate_dmn_invalid_xml():
    ok, err = validate_dmn(INVALID_XML)
    assert ok is False


def test_validate_dmn_no_decision():
    ok, err = validate_dmn("<?xml version='1.0'?><definitions/>")
    assert ok is False
    assert "decision" in err.lower()


# ── create_workflow + run_engine_steps ────────────────────────────────────────

def test_create_workflow_simple():
    wf = create_workflow(VALID_BPMN, "TestProcess")
    assert wf is not None


def test_run_engine_steps_simple_process_completes():
    """A start → end process with no human tasks completes immediately."""
    wf = create_workflow(VALID_BPMN, "TestProcess")
    human_tasks = run_engine_steps(wf)
    assert human_tasks == []
    assert is_completed(wf)


def test_run_engine_steps_user_task_blocks():
    """A process with a UserTask should stop and surface a human task."""
    wf = create_workflow(BPMN_WITH_USER_TASK, "ReviewProcess")
    human_tasks = run_engine_steps(wf)
    assert len(human_tasks) == 1
    assert human_tasks[0].task_name == "review"
    assert not is_completed(wf)


def test_create_workflow_with_initial_variables():
    wf = create_workflow(VALID_BPMN, "TestProcess", initial_variables={"key": "value"})
    from app.engine.runner import get_variables
    assert get_variables(wf)["key"] == "value"


# ── serialize / deserialize ───────────────────────────────────────────────────

def test_serialize_deserialize_roundtrip():
    wf = create_workflow(VALID_BPMN, "TestProcess")
    run_engine_steps(wf)
    state = serialize_workflow(wf)
    assert isinstance(state, dict)
    restored = deserialize_workflow(state)
    assert is_completed(restored)


def test_serialize_workflow_is_json_compatible():
    import json
    wf = create_workflow(VALID_BPMN, "TestProcess")
    run_engine_steps(wf)
    state = serialize_workflow(wf)
    # Must be JSON-serializable (for DB JSONB storage)
    json.dumps(state)
