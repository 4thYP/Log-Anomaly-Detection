from fastapi import APIRouter, BackgroundTasks, Depends
from app.models.log_models import LogCreate, LogResponse
from app.services.log_service import LogService, get_log_service

router = APIRouter()

# # Background processing function
# async def process_log_background(log: LogInternal):
#     print(f"Processing log ID: {log.id}")
#     logs_storage.append(log)

@router.post("/", response_model=LogResponse)
async def ingest_log(
    log: LogCreate, 
    background_tasks: BackgroundTasks, 
    service: LogService = Depends(get_log_service)
):
    """
    HTTP layer only.
    Business logic delegated to service.
    """
    internal_log = await service.create_log(log)

    # # Schedule background processing
    # background_tasks.add_task(process_log_background, internal_log)

    return LogResponse(
        id=internal_log.id, 
        message="Log accepted for processing"
    )

@router.get("/")
async def get_logs(
    service: LogService = Depends(get_log_service)
):
    return await service.get_all_logs()
