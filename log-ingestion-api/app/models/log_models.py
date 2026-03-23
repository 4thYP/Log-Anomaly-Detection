from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict
from uuid import UUID, uuid4
from enum import Enum

class ServerType(str, Enum):
    LINUX = "linux"
    WINDOWS = "windows"
    HPC = "hpc"
    HEALTHAPP = "healthapp"
    ZOOKEEPER = "zookeeper"

# Incoming log schema (from client)
class LogCreate(BaseModel):
    sid: str  # server id
    timestamp: datetime
    server_type: ServerType
    log_file: str
    message: str

    metadata: Optional[Dict] = None

# Internal processed log schema
class LogInternal(LogCreate):
    id: UUID = Field(default_factory=uuid4)
    ingested_at: datetime = Field(default_factory=datetime.now)

# Response schema (what API returns)
class LogResponse(BaseModel):
    id: UUID
    message: str
