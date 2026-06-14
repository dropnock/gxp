# ADR-005: Valkey (Redis fork) for messaging and caching

**Status:** Accepted
**Date:** 2026-06-13

## Decision

Valkey (BSD-3-Clause) is used instead of Redis because Redis re-licensed under SSPL in 2024, which is not OSI-approved and incompatible with commercial use in some interpretations. Valkey is a drop-in compatible fork maintained by the Linux Foundation under the BSD-3-Clause license.

## Consequences

Positive: consistent with open source commercial-use constraint; air-gap compatible.
Negative: see individual ADR for trade-offs.
