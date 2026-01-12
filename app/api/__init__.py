"""
API Routers.

FastAPI routers organized by domain for the Prismatic Engine.
"""

from app.api.creation_routes import router as creation_router
from app.api.ingestion_routes import router as ingestion_router

__all__ = ["creation_router", "ingestion_router"]

