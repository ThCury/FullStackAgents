from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import BACKEND_CONFIG, BackendConfig, Settings, get_settings
from container import Container
from routes.health import router as health_router
from routes.projects import router as projects_router
from routes.runs import router as runs_router


def create_app(
    settings: Settings | None = None, backend_config: BackendConfig | None = None
) -> FastAPI:
    active_settings = settings or get_settings()
    active_backend_config = backend_config or BACKEND_CONFIG

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = Container(active_settings, active_backend_config)
        yield

    app = FastAPI(title="FullStack Agents", version="0.1.0", lifespan=lifespan)
    # O frontend Vite roda em outra origem em desenvolvimento.
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=active_backend_config.cors_allow_origin_regex,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(projects_router)
    app.include_router(runs_router)
    return app


app = create_app()
