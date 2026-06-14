# ADR-001: Monorepo architecture

**Status:** Accepted
**Date:** 2026-06-13

## Decision

We use a single monorepo (uv workspace for Python, pnpm workspace for TypeScript) to keep all services, shared packages, and infrastructure config in one place. This simplifies dependency management, cross-service refactoring, and air-gap bundle creation.

## Consequences

Positive: consistent with open source commercial-use constraint; air-gap compatible.
Negative: see individual ADR for trade-offs.
