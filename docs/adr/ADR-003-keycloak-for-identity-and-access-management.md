# ADR-003: Keycloak for identity and access management

**Status:** Accepted
**Date:** 2026-06-13

## Decision

Keycloak (Apache 2.0) is the IAM solution because it supports OIDC, SAML, LDAP federation, mandatory MFA authentication flows, and service account OAuth2 — all required for FedRAMP compliance. It runs fully on-premises with no cloud dependencies.

## Consequences

Positive: consistent with open source commercial-use constraint; air-gap compatible.
Negative: see individual ADR for trade-offs.
