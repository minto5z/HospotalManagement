"""
Main API router for v1 endpoints
"""
from fastapi import APIRouter

from app.api.v1.endpoints import patients, auth, users, analytics

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["user-management"])
api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

# Future endpoints to be added:
# from app.api.v1.endpoints import doctors, appointments, resources
# api_router.include_router(doctors.router, prefix="/doctors", tags=["doctors"])
# api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
# api_router.include_router(resources.router, prefix="/resources", tags=["resources"])

@api_router.get("/")
async def api_root():
    return {"message": "Hospital Management System API v1"}