import time
from fastapi import Request

async def request_logging_middleware(request: Request, call_next):
    start_time = time.time()

    # Process request
    response = await call_next(request)

    process_time = time.time() - start_time

    print(
        f"{request.method} {request.url.path}"
        f"completed_in={process_time:.4f}s"
    )

    return response