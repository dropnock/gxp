# ADR-002: SpiffWorkflow for BPMN and DMN execution

**Status:** Accepted
**Date:** 2026-06-13

## Decision

SpiffWorkflow (LGPL-2.1) is chosen as the BPMN 2.0 and DMN 1.3 execution engine because it is pure Python, fully open source, supports serialization of workflow state to JSON, and integrates natively with FastAPI + Celery. It is used as an installed library (pip install), satisfying the LGPL dynamic linking requirement without imposing LGPL on GXP source code.

## Consequences

Positive: consistent with open source commercial-use constraint; air-gap compatible.
Negative: see individual ADR for trade-offs.
