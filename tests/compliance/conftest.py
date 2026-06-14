"""
Static compliance test helpers.
These tests make no network or DB calls — they inspect source code,
model definitions, and migration files to verify NIST 800-53 controls.
"""
import importlib
import sys
from pathlib import Path

# Make all service packages importable without installed dependencies
# by patching sys.path before any test module is imported.
REPO_ROOT = Path(__file__).parents[2]

def _add_service_path(service: str):
    path = REPO_ROOT / "services" / service
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

def _add_shared():
    shared = REPO_ROOT / "packages" / "py-shared"
    if str(shared) not in sys.path:
        sys.path.insert(0, str(shared))

_add_shared()
for svc in [
    "audit-service", "app-service", "case-service",
    "document-service", "tenant-service", "workflow-service",
]:
    _add_service_path(svc)
