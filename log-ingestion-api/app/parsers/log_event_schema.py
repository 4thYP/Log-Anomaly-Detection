"""
Unified Log Event Schema - Used by all parsers

This module defines the standardized schema that ALL parsers (Linux, Windows, Zookeeper)
must produce. This ensures:
- Consistent feature extractor input
- Compatible LSTM sequence building
- Predictable metadata structure
- Type safety across the pipeline

KEY PRINCIPLES:
======================
1. Top-level fields are REQUIRED for all events (event_type, event_group, component, 
   template, template_id, timestamp, status)
   
2. All optional/context-specific fields go into "metadata" dict
   
3. timestamp is ALWAYS extracted from log (required, ISO 8601 string format)

4. event_group provides coarse categorization (connection, session, error, etc)
   event_type provides fine-grained categorization (connection_received, 
   connection_broken, etc)

5. template_id is numeric (int), normalized from template CSV (E1 -> 1, E40 -> 40)

6. metadata dict contains:
   - user, ip, hostname, peer_id, session_id (entity identifiers)
   - hresult, error_code, exit_code (error details)
   - Any other domain-specific fields
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Optional, Any
from enum import Enum


# ==============================================================================
# EVENT GROUP ENUMS - Consistent across all log types
# ==============================================================================

class EventGroup(str, Enum):
    """Coarse-grained event categorization"""
    AUTHENTICATION = "authentication"  # SSH failures, auth checks (Linux)
    CONNECTION = "connection"          # TCP/connection events (all types)
    SESSION = "session"                # Session established/expired (all types)
    WORKER = "worker"                  # Background worker threads (Zookeeper)
    ELECTION = "election"              # Leader election (Zookeeper)
    QUORUM = "quorum"                  # Consensus/quorum (Zookeeper)
    TRANSACTION = "transaction"        # NT/CSI transactions (Windows)
    PACKAGE = "package"                # Package operations (Windows)
    SERVICE = "service"                # Service lifecycle (Linux/Windows)
    ERROR = "error"                    # Generic errors
    SYSTEM = "system"                  # Boot, kernel info (informational)


# ==============================================================================
# EVENT TYPE ENUMS - Granular, organized by group
# ==============================================================================

class LinuxEventType(str, Enum):
    """Linux-specific event types"""
    # Authentication
    AUTH_FAILURE = "auth_failure"           # E16-E19
    AUTH_CHECK = "auth_check"               # E27
    AUTH_ERROR = "auth_error"               # SSH error messages
    
    # Connection/Session (FTP)
    FTP_CONNECT = "ftp_connect"             # E29
    FTP_TIMEOUT = "ftp_timeout"             # FTP timeout
    FTP_LOGIN = "ftp_login"                 # E9 (anonymous FTP)
    
    # Session Management
    SESSION_OPENED = "session_opened"       # E102, E103
    SESSION_CLOSED = "session_closed"       # E101
    
    # Service
    SERVICE_START = "service_start"         # E38 (startup succeeded)
    SERVICE_STOP = "service_stop"           # E37 (cupsd shutdown)
    
    # Error
    ALERT_ERROR = "alert_error"             # E8 (ALERT exited abnormally)
    
    # System
    KERNEL_INFO = "kernel_info"             # Bot, memory, CPU info
    SYSTEM_INFO = "system_info"             # Generic informational
    UNKNOWN = "unknown"                     # Couldn't parse


class WindowsEventType(str, Enum):
    """Windows-specific event types"""
    # Transaction
    TRANSACTION_CREATE = "transaction_create"      # Created NT transaction
    TRANSACTION_INITIALIZE = "transaction_initialize"  # CSI Transaction initialized
    TRANSACTION_DESTROY = "transaction_destroy"    # CSI Transaction destroyed
    
    # Session
    SESSION_INIT = "session_init"           # Session initialized
    SESSION_DESTROY = "session_destroy"     # Session destroyed
    
    # Package
    PACKAGE_APPLICABILITY = "package_applicability"  # Package applicability check
    PACKAGE_ERROR = "package_error"         # Failed to open package
    
    # Service
    SERVICE_START = "service_start"         # TrustedInstaller starts
    SERVICE_INIT_START = "service_init_start"  # Starting initialization
    SERVICE_INIT_END = "service_init_end"   # Ending initialization
    SERVICE_STOP = "service_stop"           # Ending main loop
    
    # Error/Telemetry
    SQM_UPLOAD_FAILED = "sqm_upload_failed"     # Failed to upload SQM data
    MANIFEST_ERROR = "manifest_error"       # Manifest parsing error
    PARSE_ERROR = "parse_error"             # Parse error
    
    # System
    LOAD_SERVICING_STACK = "load_servicing_stack"  # Loaded servicing stack
    SCAVENGE = "scavenge"                   # Scavenge operation
    UNKNOWN = "unknown"


class ZookeeperEventType(str, Enum):
    """Zookeeper-specific event types"""
    # Connection
    CONNECTION_RECEIVED = "connection_received"         # E40
    CONNECTION_BROKEN = "connection_broken"             # E11
    CONNECTION_OLD = "connection_old"                   # E12
    CHANNEL_ERROR = "channel_error"                     # E5
    GOODBYE = "goodbye"                                 # E1
    ACCEPTED_SOCKET = "accepted_socket"                 # E2
    
    # Session
    SESSION_ESTABLISHED = "session_established"         # E13
    SESSION_EXPIRED = "session_expired"                 # E15
    SESSION_REVALIDATION = "session_revalidation"       # E41
    CLIENT_NEW_SESSION = "client_new_session"           # E7
    CLIENT_RENEW_SESSION = "client_renew_session"       # E8
    
    # Worker
    WORKER_INTERRUPTED = "worker_interrupted"           # E24
    WORKER_INTERRUPT_SEND = "worker_interrupt_send"     # E25
    WORKER_LEAVING = "worker_leaving"                   # E42
    
    # Election
    ELECTION_NOTIFICATION_TIMEOUT = "election_notification_timeout"  # E31
    ELECTION_NOTIFICATION = "election_notification"     # E32-E37
    ELECTION_STATE_CHANGE = "election_state_change"     # E18, E26
    NEW_ELECTION = "new_election"                       # E30
    
    # Quorum
    QUORUM_ACHIEVED = "quorum_achieved"                 # E22
    QUORUM_SMALLER_ID = "quorum_smaller_id"             # E23
    FOLLOWER_INFO = "follower_info"                     # E17
    
    # Error
    EXCEPTION = "exception"                             # E49, E50
    SERVER_NOT_RUNNING = "server_not_running"           # E14
    CAUGHT_EOF = "caught_eof"                           # E6
    
    # Service/System
    STARTING_QUORUM_PEER = "starting_quorum_peer"       # E47
    UNKNOWN = "unknown"


# ==============================================================================
# UNIFIED SCHEMA - All parsers must return this
# ==============================================================================

@dataclass
class ParsedLogEvent:
    """
    Unified log event schema.
    
    All parsers (Linux, Windows, Zookeeper) MUST return events conforming to this schema.
    
    REQUIRED FIELDS (must always be present):
    - event_type: str               Granular event classification (auth_failure, connection_received, etc)
    - event_group: str              Coarse event category (authentication, connection, error, etc)
    - component: str                Source component (sshd, CBS, QuorumPeer, etc)
    - template: str                 Normalized log template with <*> placeholders
    - template_id: int              Numeric ID from template CSV (E1 -> 1, E40 -> 40)
    - timestamp: str                ISO 8601 timestamp extracted from log (REQUIRED, not computed)
    - status: str                   Event outcome (success, failure, warning, info)
    
    OPTIONAL/CONTEXT FIELDS (stored in metadata dict):
    - user: str                     Username (Linux, Windows)
    - ip: str or remote_ip: str     Client/source IP address
    - hostname: str                 Hostname/domain name
    - peer_id: int                  Peer/node ID (Zookeeper)
    - session_id: str               Session identifier (Zookeeper, Windows)
    - hresult: str                  Windows HRESULT code (0x...)
    - error_code: str               Generic error code
    - exit_code: int                Process exit code
    - Any other domain-specific fields
    """
    
    # REQUIRED TOP-LEVEL FIELDS
    event_type: str
    event_group: str
    component: str
    template: str
    template_id: int
    timestamp: str                              # ISO 8601 string, extracted from log
    status: str                                 # success, failure, warning, info, unknown
    
    # OPTIONAL FIELDS - stored in metadata dict
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # INTERNAL FIELDS
    raw_message: str = ""                       # Original log message
    parsed_successfully: bool = True
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "event_type": self.event_type,
            "event_group": self.event_group,
            "component": self.component,
            "template": self.template,
            "template_id": self.template_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "metadata": self.metadata,
            "parsed_successfully": self.parsed_successfully,
            "confidence": self.confidence,
        }
    
    @classmethod
    def unknown_event(cls, log_line: str, component: str = "unknown", 
                     error: str = "", timestamp: str = "") -> "ParsedLogEvent":
        """
        Factory method for unparseable logs.
        
        Args:
            log_line: Original log line that couldn't be parsed
            component: Component name (or "unknown")
            error: Error description
            timestamp: ISO 8601 timestamp if available
            
        Returns:
            ParsedLogEvent instance marked as unparsed
        """
        return cls(
            event_type="unknown",
            event_group="system",
            component=component,
            template="",
            template_id=0,
            timestamp=timestamp or "",
            status="unknown",
            metadata={"error": error} if error else {},
            raw_message=log_line,
            parsed_successfully=False,
            confidence=0.0
        )


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def template_id_from_csv(csv_id: str) -> int:
    """
    Convert template CSV ID (E1, E40, etc) to numeric integer.
    
    Args:
        csv_id: String like "E1", "E40", "E100"
        
    Returns:
        Integer like 1, 40, 100
        
    Examples:
        >>> template_id_from_csv("E1")
        1
        >>> template_id_from_csv("E40")
        40
    """
    if isinstance(csv_id, int):
        return csv_id
    if isinstance(csv_id, str):
        return int(csv_id.lstrip('E'))
    return 0


# ==============================================================================
# EXAMPLE USAGE - Shows field mapping for each log type
# ==============================================================================

"""
LINUX EXAMPLE:
==============
Raw: "Jun 14 15:16:01 combo sshd(pam_unix)[19939]: authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=218.188.2.4 user=root"

ParsedLogEvent(
    event_type="auth_failure",
    event_group="authentication",
    component="sshd",
    template="authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*> user=<*>",
    template_id=18,                           # E18
    timestamp="2015-06-14T15:16:01",         # EXTRACTED from header, ISO format
    status="failure",
    metadata={
        "user": "root",
        "ip": "218.188.2.4",
        "uid": 0,
        "pid": 19939,
        "hostname": "combo"
    }
)

---

WINDOWS EXAMPLE:
================
Raw: "2016-09-28 04:30:31, Info                  CBS    Created NT transaction (seq 1), objectname [6]"(null)""

ParsedLogEvent(
    event_type="transaction_create",
    event_group="transaction",
    component="CBS",
    template="Created NT transaction (seq <*>), objectname [<*>]\"(null)\"",
    template_id=2,                            # E2
    timestamp="2016-09-28T04:30:31",         # EXTRACTED from header
    status="success",
    metadata={
        "sequence_number": 1,
        "object_name": "[6]\"(null)\""
    }
)

---

ZOOKEEPER EXAMPLE:
==================
Raw: "2015-07-29 19:04:12,394 - INFO  [/10.10.34.11:3888:QuorumCnxManager$Listener@493] - Received connection request /10.10.34.11:45307"

ParsedLogEvent(
    event_type="connection_received",
    event_group="connection",
    component="QuorumCnxManager$Listener",
    template="Received connection request /<*>:<*>",
    template_id=40,                           # E40
    timestamp="2015-07-29T19:04:12.394",     # EXTRACTED from log (with milliseconds)
    status="success",
    metadata={
        "remote_ip": "10.10.34.11",
        "remote_port": 45307,
        "local_ip": "10.10.34.11",
        "local_port": 3888,
        "line_number": 493
    }
)
"""
