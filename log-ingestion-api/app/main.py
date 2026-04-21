from fastapi import FastAPI
from app.routers import logs
from app.middleware.request_logger import request_logging_middleware
from app.repositories.log_repository import LogRepository
from app.services.log_service import LogService

app = FastAPI(title="Log Ingestion API")

app.middleware("http")
(request_logging_middleware)

@app.on_event("startup")
async def startup_event():
    """
    Initialize shared services
    """
    repository = LogRepository()
    service = LogService(repository)

    app.state.log_service = service

@app.get("/")
async def root():
    return {"status": "API running..."}

app.include_router(
    logs.router,
    prefix="/logs",
    tags=["Logs"]
)