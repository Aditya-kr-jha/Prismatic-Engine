from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

# Use the new module paths
from app.api.ingestion_routes import router as ingestion_router
from app.api.classification_routes import router as classification_router
from app.db.db_session import create_db_and_tables
from app.infra.http import HTTPClientManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for database initialization
    and resource management.
    """
    # Startup: Initialize the database tables
    print("✨ Prismatic Engine: Initializing Core Systems...")
    create_db_and_tables()

    # Startup: Initialize HTTP clients
    client_manager = HTTPClientManager()
    await client_manager.startup()
    app.state.clients = client_manager

    yield

    # Shutdown: Close HTTP clients
    await client_manager.shutdown()

    # Shutdown: Clean up resources if necessary
    print("🌑 Prismatic Engine: Shutting down...")


app = FastAPI(
    lifespan=lifespan,
    title="Prismatic Engine API",
    description=(
        "The backend core for the Prismatic Engine. "
        "A large-scale automation system that refracts raw psychological insights "
        "into a spectrum of 21 weekly Instagram assets (Quotes, Carousels, Reels)."
    ),
    version="1.0.0",
)

# CORS Configuration - Allow external access (e.g., from a frontend dashboard or automation tools)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Recommend restricting this to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(classification_router, prefix="/api/v1")


@app.get("/")
def root():
    """
    Root endpoint to verify the engine is online and identifying itself.
    """
    return {
        "system": "Prismatic Engine",
        "status": "Online",
        "mode": "Refraction",
        "docs_url": "/docs",
        "message": "Infinite Content Through Intelligent Refraction.",
    }


@app.get("/health")
def health_check():
    """
    Health check endpoint for monitoring tools (e.g., Docker, K8s).
    """
    return {"status": "healthy", "core_systems": "nominal"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app", host="127.0.0.1", port=8000, reload=True, log_level="info"
    )
