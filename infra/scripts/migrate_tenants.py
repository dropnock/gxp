#!/usr/bin/env python3
"""
Multi-tenant Alembic migration runner.

Runs `alembic upgrade head` for every active tenant schema across every service database.
Uses the tenant list from the tenant-service database (platform.tenants table).

Usage:
    python infra/scripts/migrate_tenants.py [--service <name>] [--tenant <slug>]

Options:
    --service   Run migrations for a single service only (e.g. 'app-service')
    --tenant    Run migrations for a single tenant only (e.g. 'dot')
    --dry-run   Print commands without executing them
"""
from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

import asyncpg

REPO_ROOT = Path(__file__).parent.parent.parent

# Mapping: service name → (alembic.ini path, DATABASE_URL env var name)
SERVICES: dict[str, tuple[Path, str]] = {
    "app-service":          (REPO_ROOT / "services/app-service",      "APP_SERVICE_DB_URL"),
    "workflow-service":     (REPO_ROOT / "services/workflow-service",  "WORKFLOW_SERVICE_DB_URL"),
    "case-service":         (REPO_ROOT / "services/case-service",      "CASE_SERVICE_DB_URL"),
    "document-service":     (REPO_ROOT / "services/document-service",  "DOCUMENT_SERVICE_DB_URL"),
    "audit-service":        (REPO_ROOT / "services/audit-service",     "AUDIT_SERVICE_DB_URL"),
}

# Fallback URLs for local dev (override with env vars in CI / prod)
DEFAULT_URLS: dict[str, str] = {
    "APP_SERVICE_DB_URL":       "postgresql://postgres:changeme_dev@localhost:5433/gxp_apps",
    "WORKFLOW_SERVICE_DB_URL":  "postgresql://postgres:changeme_dev@localhost:5434/gxp_workflow",
    "CASE_SERVICE_DB_URL":      "postgresql://postgres:changeme_dev@localhost:5435/gxp_case",
    "DOCUMENT_SERVICE_DB_URL":  "postgresql://postgres:changeme_dev@localhost:5436/gxp_documents",
    "AUDIT_SERVICE_DB_URL":     "postgresql://postgres:changeme_dev@localhost:5437/gxp_audit",
    "TENANT_DB_URL":            "postgresql://postgres:changeme_dev@localhost:5438/gxp_tenant",
}


async def get_active_tenant_slugs(db_url: str) -> list[str]:
    """Query platform.tenants for all active tenant slugs."""
    conn = await asyncpg.connect(db_url)
    try:
        rows = await conn.fetch("SELECT slug FROM platform.tenants WHERE status = 'active' ORDER BY slug")
        return [r["slug"] for r in rows]
    finally:
        await conn.close()


def run_alembic(service_dir: Path, db_url: str, tenant_schema: str, dry_run: bool) -> bool:
    """Run alembic upgrade head for a single service + tenant schema."""
    env = {**os.environ, "DATABASE_URL": db_url, "GXP_TENANT_SCHEMA": tenant_schema}
    cmd = ["python", "-m", "alembic", "upgrade", "head"]

    if dry_run:
        print(f"  [dry-run] cd {service_dir} && GXP_TENANT_SCHEMA={tenant_schema} {' '.join(cmd)}")
        return True

    result = subprocess.run(cmd, cwd=service_dir, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}", file=sys.stderr)
        return False
    return True


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run multi-tenant Alembic migrations")
    parser.add_argument("--service", help="Migrate a single service only")
    parser.add_argument("--tenant", help="Migrate a single tenant schema only")
    parser.add_argument("--dry-run", action="store_true", help="Print without executing")
    args = parser.parse_args()

    tenant_db_url = os.environ.get("TENANT_DB_URL", DEFAULT_URLS["TENANT_DB_URL"])

    if args.tenant:
        slugs = [args.tenant]
        print(f"Targeting single tenant: {args.tenant}")
    else:
        print("Fetching active tenants from tenant-service DB...")
        slugs = await get_active_tenant_slugs(tenant_db_url)
        print(f"Found {len(slugs)} active tenant(s): {', '.join(slugs)}")

    services = {k: v for k, v in SERVICES.items() if not args.service or k == args.service}
    if not services:
        print(f"Unknown service: {args.service}", file=sys.stderr)
        sys.exit(1)

    errors: list[str] = []

    for svc_name, (svc_dir, url_env) in services.items():
        db_url = os.environ.get(url_env, DEFAULT_URLS[url_env])
        # Convert asyncpg URL to regular psycopg URL for alembic env.py
        alembic_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

        print(f"\n── {svc_name} ──")
        for slug in slugs:
            schema = f"t_{slug}"
            print(f"  {schema}...", end=" ", flush=True)
            ok = run_alembic(svc_dir, alembic_url, schema, args.dry_run)
            print("OK" if ok else "FAILED")
            if not ok:
                errors.append(f"{svc_name}/{schema}")

    if errors:
        print(f"\n{len(errors)} migration(s) failed: {errors}", file=sys.stderr)
        sys.exit(1)
    else:
        print("\nAll migrations completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
