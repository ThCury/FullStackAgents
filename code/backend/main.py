from __future__ import annotations

from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

from config import BACKEND_CONFIG, BackendConfig, Settings, get_settings
from container import Container
from routes.health import router as health_router
from routes.projects import router as projects_router
from routes.runs import router as runs_router

HTTP_REQUESTS = Counter(
    "fullstack_agents_http_requests_total",
    "Total de requisicoes HTTP recebidas pela API.",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "fullstack_agents_http_request_duration_seconds",
    "Duracao das requisicoes HTTP da API.",
    ["method", "path"],
)


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

    @app.middleware("http")
    async def observe_requests(request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        started_at = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            path = getattr(route, "path", request.url.path)
            HTTP_REQUESTS.labels(request.method, path, str(status_code)).inc()
            HTTP_REQUEST_DURATION.labels(request.method, path).observe(
                perf_counter() - started_at
            )

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    app.include_router(health_router)
    app.include_router(projects_router)
    app.include_router(runs_router)
    return app


app = create_app()
