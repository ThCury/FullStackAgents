from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from fullstack_agents.config import Settings, get_settings
from fullstack_agents.container import Container
from fullstack_agents.interfaces.http.routes import router


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.container = Container(active_settings)
        yield

    app = FastAPI(title="FullStack Agents", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()

