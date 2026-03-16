from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict
from uuid import UUID, uuid4
from enum import Enum

# Allowed log levels (validation rule)
class LogLevel(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    DEBUG = "DEBUG"

# Incoming log schema (from client)
class LogCreate(BaseModel):
    timestamp: datetime
    level: LogLevel
    service: str = Field(..., min_length=2)
    message: str = Field(..., min_length=1)

    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    action: Optional[str] = None
    metadata: Optional[Dict] = None

# Internal processed log schema
class LogInternal(LogCreate):
    id: UUID = Field(default_factory=uuid4)
    ingested_at: datetime = Field(default_factory=datetime.now)

# Response schema (what API returns)
class LogResponse(BaseModel):
    id: UUID
    message: str