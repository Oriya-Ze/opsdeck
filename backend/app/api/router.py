from fastapi import APIRouter

from app.api.routes import (
    activity_logs,
    containers,
    dashboard,
    health_checks,
    jobs,
    nodes,
    services,
    settings,
    system,
    workloads,
)

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(dashboard.router)
api_router.include_router(nodes.router)
api_router.include_router(services.router)
api_router.include_router(containers.router)
api_router.include_router(workloads.router)
api_router.include_router(jobs.router)
api_router.include_router(health_checks.router)
api_router.include_router(activity_logs.router)
api_router.include_router(settings.router)
