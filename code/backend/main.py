from fastapi import FastAPI

from routes.hello import router as hello_router

app = FastAPI(title="FullStackAgents API")
app.include_router(hello_router)
