from fastapi import APIRouter
from app.api.v1 import definitions, dmn_definitions, instances, tasks

router = APIRouter()
router.include_router(definitions.router, prefix="/workflow/definitions", tags=["workflow-definitions"])
router.include_router(dmn_definitions.router, prefix="/workflow/dmn-definitions", tags=["dmn-definitions"])
router.include_router(instances.router, prefix="/workflow/instances", tags=["workflow-instances"])
router.include_router(tasks.router, prefix="/workflow/tasks", tags=["workflow-tasks"])
