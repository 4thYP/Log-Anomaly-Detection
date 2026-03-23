from fastapi import Request
from app.models.log_models import LogCreate, LogInternal
from app.repositories.log_repository import LogRepository
from app.parsers.log_parser import LogParser
from app.parsers.parser_factory import ParserFactory
from app.features.feature_extractor_factory import FeatureExtractorFactory
from app.sequences.sequence_builder import SequenceBuilder

class LogService:
    def __init__(self, repository: LogRepository):
        self.repository = repository
        self.sequence_builder = SequenceBuilder(sequence_length=5)

    async def create_log(self, log_data: LogCreate) -> LogInternal:
        # Business logic for creating a log.
        internal_log = LogInternal(**log_data.model_dump())

        # Select parser dynamically
        parser = ParserFactory.get_parser(log_data.server_type)

        # Parse log message
        parsed_data = parser.parse(log_data.message)

        # Attach structured data
        internal_log.metadata = {
            **(internal_log.metadata or {}),
            "parsed": parsed_data
        }

        # Extract ML features
        extractor = FeatureExtractorFactory.get_extractor(log_data.server_type)
        features = extractor.extract(internal_log)

        internal_log.metadata["features"] = features

        # Build sequence
        # sequence_result = self.sequence_builder.build_sequence(internal_log)
        #
        # internal_log.metadata["sequence_ready"] = sequence_result["ready"]
        #
        # if sequence_result["ready"]:
        #     internal_log.metadata["sequence"] = sequence_result["sequence"]


        await self.repository.save(internal_log)
        return internal_log
    
    async def get_all_logs(self):
        return await self.repository.get_all()
    
# Dependency provider
def get_log_service(request: Request) -> LogService:
    return request.app.state.log_service
