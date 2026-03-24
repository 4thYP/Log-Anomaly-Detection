"""
UNIFIED PARSER SCHEMA - IMPLEMENTATION GUIDE

This document explains how to use the unified ParsedLogEvent schema across all parsers.

=== KEY CHANGES FROM CURRENT IMPLEMENTATION ===

1. ALL parsers return ParsedLogEvent (not custom dataclasses)
2. Top-level fields are standardized (event_type, event_group, component, template, 
   template_id, timestamp, status)
3. Optional domain-specific fields go in metadata dict (not as top-level attributes)
4. timestamp is REQUIRED and extracted from log (ISO 8601 string)
5. template_id is INTEGER (1, 2, 40, not "E1", "E2", "E40")

=== FIELD MAPPING BY LOG TYPE ===

LINUX:
------
Top-level (always present):
  - event_type: auth_failure | auth_check | ftp_connect | session_opened | etc
  - event_group: authentication | connection | session | service | error | system
  - component: sshd | ftpd | su | login | logrotate | kernel | etc
  - template: "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*>"
  - template_id: 16, 17, 18, 19 (from Linux_2k.log_templates.csv)
  - timestamp: "2015-06-14T15:16:01" (extracted from log header)
  - status: success | failure | unknown | info

Metadata dict (optional):
  - user: str (from "user=root")
  - ip: str (from "rhost=...")
  - hostname: str (from log header)
  - uid: int (from "uid=0")
  - pid: int (from "[19939]")
  - duration: int (for FTP timeouts)
  - exit_code: int (for alerts)


WINDOWS:
--------
Top-level (always present):
  - event_type: transaction_create | transaction_destroy | session_init | package_error | etc
  - event_group: transaction | session | package | service | error | system
  - component: CBS | CSI | etc
  - template: "Created NT transaction (seq <*>) result <*>, handle @<*>"
  - template_id: 1, 2, 3, etc (from Windows_2k.log_templates.csv)
  - timestamp: "2016-09-28T04:30:31" (extracted from log header)
  - status: success | failure | info

Metadata dict (optional):
  - hresult: str (0x80004005)
  - error_name: str (E_FAIL)
  - sequence_number: int (from "seq <*>")
  - session_id: str (from "Session: <*>_<*>")
  - client: str (client name from session)
  - package_name: str (from package operations)
  - transaction_id: str (from "@0x...")


ZOOKEEPER:
----------
Top-level (always present):
  - event_type: connection_received | connection_broken | election_notification | etc
  - event_group: connection | session | worker | election | quorum | error | service
  - component: QuorumPeer | QuorumCnxManager$Listener | QuorumCnxManager$SendWorker | etc
  - template: "Received connection request /<*>:<*>"
  - template_id: 1, 2, 5, 11, 13, 18, 22, 24, 25, 30, 31, 32, etc
  - timestamp: "2015-07-29T19:04:12.394" (with milliseconds, extracted from log)
  - status: success | failure | warning | info

Metadata dict (optional):
  - peer_id: int (from "id <*>")
  - myid: int (from "my id = <*>")
  - remote_ip: str (IP from connection)
  - remote_port: int (port from connection)
  - local_ip: str (local side IP)
  - local_port: int (local side port)
  - session_id: str (session hex ID for client sessions)
  - timeout_ms: int (session timeout)
  - election_state: str (LOOKING | FOLLOWING | LEADING)
  - proposed_leader: int (leader ID from notification)
  - zxid: str (Zookeeper transaction ID)
  - error_reason: str (from error events)
  - line_number: int (from log message format)
  - worker_type: str (SendWorker | RecvWorker)
  - notification_timeout: int (for election timeout events)


=== IMPLEMENTATION STEPS FOR EACH PARSER ===

1. Import the schema:
   from app.parsers.log_event_schema import (
       ParsedLogEvent, EventGroup, LinuxEventType, template_id_from_csv
   )

2. Parse the log line extract required fields:
   - timestamp: datetime.strptime(...) -> .isoformat() string
   - component: Extract from log format
   - event_type: Determine based on content (use enum values)
   - event_group: Map from event_type (connection->connection, auth_failure->authentication)
   - template: Normalize message with <*> placeholders
   - template_id: Use template_id_from_csv("E40") -> 40
   - status: Determine from parsing success/content

3. Build optional metadata dict:
   - Only include fields that were actually extracted
   - Don't include None values
   - Examples:
     metadata = {
         "user": user,
         "ip": ip,
         "uid": uid,
         "pid": pid
     }

4. Return ParsedLogEvent instance:
   return ParsedLogEvent(
       event_type=event_type,
       event_group=event_group,
       component=component,
       template=template,
       template_id=template_id,
       timestamp=timestamp,
       status=status,
       metadata=metadata,
       raw_message=log_line
   )

5. For unparseable logs:
   return ParsedLogEvent.unknown_event(
       log_line=log_line,
       component="unknown",
       error="Could not parse with any pattern"
   )


=== TIMESTAMP EXTRACTION - CRITICAL DETAIL ===

Each log type has different timestamp format:

LINUX:
  Format: "Mon DD HH:MM:SS"
  Example: "Jun 14 15:16:01"
  Issue: No year! Must infer from context (usually current year or from logfile name)
  Output: "2015-06-14T15:16:01"
  Code:
    from datetime import datetime
    year = 2015  # Or infer from data/Linux_2k.log -> year=2015
    dt = datetime.strptime(f"{year} {month} {day} {time}", "%Y %b %d %H:%M:%S")
    timestamp = dt.isoformat()

WINDOWS:
  Format: "YYYY-MM-DD HH:MM:SS"
  Example: "2016-09-28 04:30:31"
  Output: "2016-09-28T04:30:31"
  Code:
    dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    timestamp = dt.isoformat()

ZOOKEEPER:
  Format: "YYYY-MM-DD HH:MM:SS,mmm"
  Example: "2015-07-29 19:04:12,394"
  Output: "2015-07-29T19:04:12.394000" (include milliseconds)
  Code:
    # Handle milliseconds properly
    dt = datetime.strptime(ts_str.split(',')[0], "%Y-%m-%d %H:%M:%S")
    millis = int(ts_str.split(',')[1])
    dt = dt.replace(microsecond=millis * 1000)
    timestamp = dt.isoformat()


=== EXAMPLE: LINUX PARSER METHOD ===

def _parse_ssh(self, message: str, component: str, pid: Optional[int], 
               log_line: str, timestamp: str) -> ParsedLogEvent:
    '''Parse SSH authentication events'''
    
    if "authentication failure" in message:
        match = self.SSH_AUTH_FAILURE.search(message)
        ip = match.group("ip") if match and match.group("ip") else None
        user = match.group("user") if match and match.group("user") else None
        
        # Determine which specific auth_failure based on user
        if user == "root":
            template_id = 18  # E18
            template = "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*> user=root"
        else:
            template_id = 16  # E16
            template = "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*>"
        
        # Build metadata with only extracted fields
        metadata = {}
        if user:
            metadata["user"] = user
        if ip:
            metadata["ip"] = ip
        metadata["uid"] = 0
        if pid:
            metadata["pid"] = pid
        
        # Return unified schema
        return ParsedLogEvent(
            event_type="auth_failure",
            event_group="authentication",
            component=component,
            template=template,
            template_id=template_id,
            timestamp=timestamp,
            status="failure",
            metadata=metadata,
            raw_message=message
        )
    
    elif self.SSH_CHECK_PASS.search(message):
        return ParsedLogEvent(
            event_type="auth_check",
            event_group="authentication",
            component=component,
             template="check pass; user unknown",
            template_id=27,  # E27
            timestamp=timestamp,
            status="unknown",
            metadata={},
            raw_message=message
        )
    
    else:
        return ParsedLogEvent.unknown_event(
            log_line=log_line,
            component=component,
            error="SSH message did not match any known pattern"
        )


=== EXAMPLE: FEATURE EXTRACTOR EXPECTATIONS ===

Feature extractors will receive LogInternal with metadata["parsed"] = ParsedLogEvent.to_dict()

Example:
  log_internal.metadata["parsed"] = {
      "event_type": "auth_failure",
      "event_group": "authentication",
      "component": "sshd",
      "template": "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*>",
      "template_id": 16,
      "timestamp": "2015-06-14T15:16:01",
      "status": "failure",
      "metadata": {
          "user": "root",
          "ip": "218.188.2.4",
          "uid": 0,
          "pid": 19939
      }
  }

Feature extractor should:
  parsed = log_internal.metadata["parsed"]
  timestamp = datetime.fromisoformat(parsed["timestamp"])
  event_type = parsed["event_type"]
  event_group = parsed["event_group"]
  metadata = parsed["metadata"]
  
  # Extract entity IDs from metadata
  user = metadata.get("user")
  ip = metadata.get("ip")
  peer_id = metadata.get("peer_id")
  
  # Update per-server state using log_internal.sid
  server_id = log_internal.sid
