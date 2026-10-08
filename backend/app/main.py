"""Jev Studio — FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from .db import SessionLocal
    from .services.demo import seed_demo

    with SessionLocal() as db:
        seed_demo(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "app": settings.app_name}

    # Routers are registered here (phases 4-7 wire in engine + persistence).
    from .api.routes import api_router

    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
