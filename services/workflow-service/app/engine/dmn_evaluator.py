"""
Standalone DMN decision table evaluation using SpiffWorkflow's DMN engine.

Used by the ad-hoc evaluate endpoint (POST /workflow/dmn-definitions/{id}/evaluate)
so developers can test decision tables without running a full workflow.

For Business Rule Tasks within a BPMN process, DMN evaluation is handled
automatically by SpiffWorkflow when the DMN is loaded via parser.add_dmn_str().
"""
from __future__ import annotations

import logging
from typing import Any

from lxml import etree

logger = logging.getLogger(__name__)


def evaluate_dmn(dmn_xml: str, input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluate a DMN decision table against the provided input data.
    Returns the output variables as a dict.

    Raises ValueError on parse error or when no rule matches (if hit-policy is UNIQUE/FIRST).
    """
    try:
        # Import SpiffWorkflow's DMN internals
        from SpiffWorkflow.dmn.parser.DMNParser import DMNParser
        from SpiffWorkflow.dmn.engine.DMNEngine import DMNEngine

        root = etree.fromstring(dmn_xml.encode())
        dmn_parser = DMNParser(None, root, filename="decision.dmn")

        decision = dmn_parser.decision
        if not decision:
            raise ValueError("No decision found in DMN XML")

        # Evaluate each decision table in order
        results: dict[str, Any] = {}
        for table in decision.decisionTables:
            engine = DMNEngine(table)
            # SpiffWorkflow DMN engine expects a dict-like context
            output = engine.decide(input_data)
            if output is not None:
                if isinstance(output, list):
                    for row in output:
                        results.update(row)
                elif isinstance(output, dict):
                    results.update(output)

        return results

    except ImportError:
        # SpiffWorkflow version differences — fall back to simpler internal path
        return _evaluate_dmn_fallback(dmn_xml, input_data)
    except Exception as e:
        raise ValueError(f"DMN evaluation error: {e}") from e


def _evaluate_dmn_fallback(dmn_xml: str, input_data: dict[str, Any]) -> dict[str, Any]:
    """
    Fallback evaluator: wraps the DMN in a minimal BPMN process and uses
    the full SpiffWorkflow engine.  Slower but handles all DMN features.
    """
    from app.engine.runner import create_workflow, run_engine_steps, get_variables

    # Parse the decision id from the DMN
    root = etree.fromstring(dmn_xml.encode())
    decisions = root.findall(".//{*}decision")
    if not decisions:
        raise ValueError("No <decision> found in DMN XML")
    decision_id = decisions[0].get("id", "decision")

    # Wrap in a minimal BPMN: StartEvent → BusinessRuleTask → EndEvent
    bpmn_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:camunda="http://camunda.org/schema/1.0/bpmn"
                  targetNamespace="http://gxp.internal/dmn-eval">
  <bpmn:process id="DmnEvalProcess" isExecutable="true">
    <bpmn:startEvent id="start"/>
    <bpmn:sequenceFlow id="sf1" sourceRef="start" targetRef="brt"/>
    <bpmn:businessRuleTask id="brt" name="Evaluate" camunda:decisionRef="{decision_id}">
      <bpmn:extensionElements>
        <camunda:inputOutput>
          <camunda:outputParameter name="result">${{{decision_id}}}</camunda:outputParameter>
        </camunda:inputOutput>
      </bpmn:extensionElements>
    </bpmn:businessRuleTask>
    <bpmn:sequenceFlow id="sf2" sourceRef="brt" targetRef="end"/>
    <bpmn:endEvent id="end"/>
  </bpmn:process>
</bpmn:definitions>"""

    try:
        workflow = create_workflow(
            bpmn_xml=bpmn_xml,
            process_id="DmnEvalProcess",
            initial_variables=input_data,
            dmn_xml_list=[dmn_xml],
        )
        run_engine_steps(workflow)
        return get_variables(workflow)
    except Exception as e:
        raise ValueError(f"DMN fallback evaluation error: {e}") from e
