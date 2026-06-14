# ADR-004: MinIO for object storage

**Status:** Accepted
**Date:** 2026-06-13

## Decision

MinIO (AGPL-3.0) is used for S3-compatible on-premises object storage. The AGPL license does not impose obligations on GXP because GXP uses MinIO as an internal service and does not distribute MinIO to external parties. MinIO supports object locking (WORM) for document retention compliance.

## Consequences

Positive: consistent with open source commercial-use constraint; air-gap compatible.
Negative: see individual ADR for trade-offs.
