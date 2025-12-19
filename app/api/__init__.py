"""
API Routers.

FastAPI routers organized by domain for the Prismatic Engine.
"""

from app.api.ingestion_routes import router as ingestion_router

__all__ = ["ingestion_router"]
