from app.api.routers import audit, auth, devices, entities, health, provisioning, rooms, system
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(system.router, tags=["system"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(provisioning.router, prefix="/provisioning", tags=["provisioning"])
api_router.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(entities.router, prefix="/entities", tags=["entities"])
api_router.include_router(audit.router, prefix="/audit-events", tags=["audit"])
