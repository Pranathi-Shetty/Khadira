"""FastAPI application factory for Khadira."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import sessionmaker

from .api import (
    auth, dashboard, dispatch, finance, items, machines,
    orders, partners, production, qc, rolls,
)
from .api import purchasing as purchasing_api
from .api import settings as settings_api
from .config import Settings, get_settings
from .db import make_session_factory
from .services.common import DomainError


def create_app(session_factory: sessionmaker | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Khadira ERP API",
        version="1.0.0",
        description="Yarn purchasing, production, QC, dispatch and invoicing for Khadira.",
    )
    app.state.settings = settings
    app.state.session_factory = session_factory or make_session_factory(settings.database_url, settings.serverless)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    def domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.get("/", tags=["meta"])
    def root() -> dict:
        return {
            "status": "ok",
            "app": "Khadira ERP",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/api/health",
        }

    @app.get("/api/health", tags=["meta"])
    def health() -> dict:
        return {"status": "ok", "app": "Khadira"}

    for module in (auth, items, partners, purchasing_api, orders, machines,
                   production, rolls, qc, dispatch, finance, dashboard, settings_api):
        app.include_router(module.router)

    return app
