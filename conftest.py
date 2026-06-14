"""
Root conftest — adds all service and shared package paths to sys.path so
test modules can import service code without the packages being installed.
"""
import sys
from pathlib import Path

REPO = Path(__file__).parent

_paths = [
    REPO / "packages" / "py-shared",
    REPO / "services" / "app-service",
    REPO / "services" / "audit-service",
    REPO / "services" / "case-service",
    REPO / "services" / "document-service",
    REPO / "services" / "workflow-service",
    REPO / "services" / "tenant-service",
    REPO / "services" / "notification-service",
]

for p in _paths:
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)
