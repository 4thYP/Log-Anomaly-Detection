from typing import List
from app.models.log_models import LogInternal

class LogRepository:
    def __init__(self):
        self._logs: List[LogInternal] = []

    async def save(self, log: LogInternal) -> None:
        self._logs.append(log)

    async def get_all(self) -> List[LogInternal]:
        return self._logs