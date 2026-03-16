from fastapi import Request
from app.models.log_models import LogCreate, LogInternal
from app.repositories.log_repository import LogRepository
from app.parsers.log_parser import LogParser
from app.features.feature_extractor import FeatureExtractor

class LogService:
    def __init__(self, repository: LogRepository):
        self.repository = repository
        self.parser = LogParser()
        self.feature_extractor = FeatureExtractor()

    async def create_log(self, log_data: LogCreate) -> LogInternal:
        # Business logic for creating a log.
        internal_log = LogInternal(**log_data.model_dump())

        # Parse log message
        parsed_data = self.parser.parse(log_data.message)

        # Attach structured data
        internal_log.metadata = {
            **(internal_log.metadata or {}),
            "parsed": parsed_data
        }

        # Extract ML features
        feattures = self.feature_extractor.extract(internal_log)

        internal_log.metadata["features"] = feattures

        await self.repository.save(internal_log)
        return internal_log
    
    async def get_all_logs(self):
        return await self.repository.get_all()
    
# Dependency provider
def get_log_service(request: Request) -> LogService:
    return request.app.state.log_service