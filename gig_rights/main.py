"""Main FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from gig_rights.api.routes import router as api_router
from gig_rights.db.session import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Automatically create SQLite database tables on server startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="GigRights API",
    description="UK Statutory Holiday Entitlement Calculation Engine & Audit Trail (2026 Rules)",
    version="1.0.0",
    lifespan=lifespan,
)

# Register the API routes (/classify, /calculate, /audit)
app.include_router(api_router)


@app.get("/health", tags=["System"])
def health_check():
    """Simple API health check endpoint."""

    return {"status": "ok", "service": "GigRights API"}
