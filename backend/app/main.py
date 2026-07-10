"""FastAPI application entry point.

Module boundaries follow the current demo scope in
docs/decisions/0006-demo-mvp-scope-freeze.md.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.routers import debug, demo
from app.schemas import HealthResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""

    settings: Settings = app.state.settings
    logging.basicConfig(level=settings.backend_log_level.upper())
    logger.info(
        "Starting %s in %s mode (gen_model=%s, embed_model=%s, search=%s)",
        settings.app_name,
        settings.app_env,
        settings.gen_model,
        settings.embed_model,
        settings.search_gateway_enabled,
    )
    yield
    logger.info("Shutting down %s", settings.app_name)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="Knowledge Base RAG API",
        description="香港金融公司内部知识库 / RAG 助手 API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings

    # CORS: restrict to known origins in production
    if settings.app_env == "development":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://localhost:3000"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/api/v1/health", tags=["system"])
    def health_check() -> HealthResponse:
        """Health check endpoint.

        Returns basic service status. Does not expose sensitive config.
        """

        return HealthResponse(service=app.state.settings.app_name, version="0.1.0")

    app.include_router(debug.router)
    app.include_router(demo.router)

    return app


# Module-level app instance for uvicorn: uvicorn app.main:app
app = create_app()
