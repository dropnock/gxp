from fastapi import APIRouter
from app.api.v1 import events, reports

router = APIRouter()
router.include_router(events.router, prefix="/audit/events", tags=["audit-events"])
router.include_router(reports.router, prefix="/audit/reports", tags=["audit-reports"])
