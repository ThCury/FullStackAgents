from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_database
from app.views.auth_view import router as auth_router
from app.views.profile_view import router as profile_router
from app.views.todo_view import router as todo_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title="Login Todo API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(todo_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
