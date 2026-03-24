"""
Production-grade Linux log parser for Loghub Linux logs.
Handles SSH, FTP, session, and system events with robust regex patterns.
Uses unified ParsedLogEvent schema.
"""

import re
from typing import Dict, Optional, Any
from datetime import datetime

from app.parsers.base_parser import BaseParser
from app.parsers.log_event_schema import (
    ParsedLogEvent, EventGroup, LinuxEventType, template_id_from_csv
)


class LinuxParser(BaseParser):
    """
    Parser for Linux syslog entries from Loghub dataset.
    
    Handles:
    - SSH authentication events (sshd with pam_unix)
    - Session management (su, login)
    - FTP connection events
    - System alerts and services
    - Kernel boot messages
    
    Note: Linux syslog entries lack a year. By default, assumes year 2015.
    Override context_year in __init__ if processing a different year's logs.
    """

    # ============================================================================
    # REGEX PATTERNS - Production-grade with named groups
    # ============================================================================

    # Header pattern: "Mon DD HH:MM:SS host component[pid]: message"
    HEADER_PATTERN = re.compile(
        r"^(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})\s+"
        r"(?P<host>\S+)\s+(?P<component_full>\S+?)(?:\[(?P<pid>\d+)\])?: (?P<message>.*)"
    )

    # Month name to number mapping
    MONTH_MAP = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }

    # SSH Authentication Patterns
    SSH_AUTH_FAILURE = re.compile(
        r"authentication failure;.*?(?:rhost=(?P<ip>\S+))?\s*(?:user=(?P<user>\S+))?"
    )
    SSH_CHECK_PASS = re.compile(r"check pass; user unknown")
    SSH_AUTH_ERROR = re.compile(
        r"(?P<error>Permission denied|Software caused connection abort)"
    )

    # Session Patterns
    SESSION_OPENED = re.compile(
        r"session opened for user (?P<user>\S+)\s+by (?:LOGIN)?\(?uid=(?P<uid>\d+)\)?"
    )
    SESSION_CLOSED = re.compile(r"session closed for user (?P<user>\S+)")

    # FTP Patterns
    FTP_CONNECTION = re.compile(
        r"connection from (?P<ip>[\d.]+)\s+\((?P<hostname>[^)]+)\)\s+at\s+(?P<timestamp>.*)"
    )
    FTP_TIMEOUT = re.compile(
        r"User (?P<user>\S+) timed out after (?P<duration>\d+) seconds"
    )
    FTP_LOGIN = re.compile(
        r"ANONYMOUS FTP LOGIN FROM (?P<ip>[\d.]+),\s+\((?P<email>[^)]+)\)"
    )

    # System/Service Patterns
    ALERT_PATTERN = re.compile(
        r"ALERT exited abnormally with \[(?P<exit_code>\d+)\]"
    )
    SERVICE_SUCCESS = re.compile(r"(?P<service>\w+) startup succeeded")
    SERVICE_FAILED = re.compile(r"(?P<service>\w+) startup failed")

    # Root login and other simple patterns
    ROOT_LOGIN = re.compile(r"ROOT LOGIN ON (?P<tty>\S+)")

    # Kernel/System info patterns
    KERNEL_INFO = re.compile(
        r"(?:Linux version|Memory:|kernel core_uses_pid|dmesg)"
    )

    def __init__(self, context_year: int = 2015):
        """
        Initialize Linux parser.
        
        Args:
            context_year: Year to use for syslog entries (default 2015 for Loghub data)
        """
        self.context_year = context_year

    # ============================================================================
    # PARSER IMPLEMENTATION
    # ============================================================================

    def parse(self, log_line: str) -> Dict[str, Any]:
        """
        Parse a single Linux syslog line.

        Args:
            log_line: Raw syslog line

        Returns:
            Dictionary representation of ParsedLogEvent
        """
        try:
            # Parse header
            header_match = self.HEADER_PATTERN.match(log_line)
            if not header_match:
                return self._build_unknown_event(log_line, "Header pattern not matched")

            groups = header_match.groupdict()
            month_str = groups.get("month", "")
            day_str = groups.get("day", "")
            time_str = groups.get("time", "")
            hostname = groups.get("host", "")
            component_full = groups.get("component_full", "")
            message = groups.get("message", "")
            pid = groups.get("pid")

            # Extract and convert timestamp
            timestamp = self._parse_timestamp(month_str, day_str, time_str)
            if not timestamp:
                return self._build_unknown_event(log_line, "Could not parse timestamp")

            # Parse component 
            component, subcomponent = self._parse_component(component_full)

            # Convert PID to int if present
            pid_int = int(pid) if pid else None

            # Route to appropriate parser based on component
            if component == "sshd":
                return self._parse_ssh(message, component, pid_int, hostname, timestamp, log_line)
            elif component == "su":
                return self._parse_session_su(message, component, pid_int, hostname, timestamp, log_line)
            elif component == "login":
                return self._parse_session_login(message, component, pid_int, hostname, timestamp, log_line)
            elif component == "ftpd":
                return self._parse_ftp(message, component, pid_int, hostname, timestamp, log_line)
            elif component == "logrotate":
                return self._parse_logrotate(message, component, hostname, timestamp, log_line)
            elif component == "kernel":
                return self._parse_kernel(message, component, hostname, timestamp, log_line)
            else:
                return self._parse_generic(component, message, pid_int, hostname, timestamp, log_line)

        except Exception as e:
            return self._build_unknown_event(log_line, str(e))

    # ============================================================================
    # COMPONENT PARSERS
    # ============================================================================

    def _parse_ssh(self, message: str, component: str, pid: Optional[int],
                   hostname: str, timestamp: str, log_line: str) -> Dict[str, Any]:
        """Parse SSH (sshd) authentication events"""
        
        # Check for authentication failure
        if "authentication failure" in message:
            match = self.SSH_AUTH_FAILURE.search(message)
            ip = match.group("ip") if match and match.group("ip") else None
            user = match.group("user") if match and match.group("user") else None

            # Determine template based on user presence
            if user:
                if user == "root":
                    template_id = 18  # E18
                    template = "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*>  user=root"
                elif user == "test":
                    template_id = 19  # E19
                    template = "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*>  user=test"
                elif user == "guest":
                    template_id = 17  # E17
                    template = "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*>  user=guest"
                else:
                    template_id = 16  # E16
                    template = "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*>"
            else:
                template_id = 16  # E16
                template = "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*>"

            # Build metadata
            metadata = {"uid": 0}
            if user:
                metadata["user"] = user
            if ip:
                metadata["ip"] = ip
            if pid:
                metadata["pid"] = pid
            if hostname:
                metadata["hostname"] = hostname

            return ParsedLogEvent(
                event_type=LinuxEventType.AUTH_FAILURE.value,
                event_group=EventGroup.AUTHENTICATION.value,
                component=component,
                template=template,
                template_id=template_id,
                timestamp=timestamp,
                status="failure",
                metadata=metadata,
                raw_message=message
            ).to_dict()

        # Check for "check pass; user unknown"
        elif self.SSH_CHECK_PASS.search(message):
            return ParsedLogEvent(
                event_type=LinuxEventType.AUTH_CHECK.value,
                event_group=EventGroup.AUTHENTICATION.value,
                component=component,
                template="check pass; user unknown",
                template_id=27,  # E27
                timestamp=timestamp,
                status="check_pass",
                metadata={"pid": pid} if pid else {},
                raw_message=message
            ).to_dict()

        # Fallback for other SSH messages
        else:
            return ParsedLogEvent(
                event_type=LinuxEventType.SSH_EVENT.value,
                event_group=EventGroup.AUTHENTICATION.value,
                component=component,
                template="",
                template_id=0,
                timestamp=timestamp,
                status="unknown",
                metadata={"pid": pid} if pid else {},
                raw_message=message,
                parsed_successfully=False,
                confidence=0.5
            ).to_dict()

    def _parse_session_su(self, message: str, component: str, pid: Optional[int],
                         hostname: str, timestamp: str, log_line: str) -> Dict[str, Any]:
        """Parse session events from su (substitute user)"""
        
        # Session opened
        if "session opened" in message:
            match = self.SESSION_OPENED.search(message)
            user = match.group("user") if match else None
            uid = int(match.group("uid")) if match and match.group("uid") else None

            metadata = {}
            if user:
                metadata["user"] = user
            if uid is not None:
                metadata["uid"] = uid
            if pid:
                metadata["pid"] = pid
            if hostname:
                metadata["hostname"] = hostname

            return ParsedLogEvent(
                event_type=LinuxEventType.SESSION_OPENED.value,
                event_group=EventGroup.SESSION.value,
                component=component,
                template="session opened for user <*> by (uid=<*>)",
                template_id=102,  # E102 (custom, not in CSV)
                timestamp=timestamp,
                status="success",
                metadata=metadata,
                raw_message=message
            ).to_dict()

        # Session closed
        elif "session closed" in message:
            match = self.SESSION_CLOSED.search(message)
            user = match.group("user") if match else None

            metadata = {}
            if user:
                metadata["user"] = user
            if pid:
                metadata["pid"] = pid
            if hostname:
                metadata["hostname"] = hostname

            return ParsedLogEvent(
                event_type=LinuxEventType.SESSION_CLOSED.value,
                event_group=EventGroup.SESSION.value,
                component=component,
                template="session closed for user <*>",
                template_id=101,  # E101 (custom)
                timestamp=timestamp,
                status="success",
                metadata=metadata,
                raw_message=message
            ).to_dict()

        else:
            return ParsedLogEvent.unknown_event(
                log_line, component, timestamp=timestamp
            ).to_dict()

    def _parse_session_login(self, message: str, component: str, pid: Optional[int],
                            hostname: str, timestamp: str, log_line: str) -> Dict[str, Any]:
        """Parse login session events"""
        
        if "session opened" in message:
            match = self.SESSION_OPENED.search(message)
            user = match.group("user") if match else None
            uid = int(match.group("uid")) if match and match.group("uid") else None

            metadata = {}
            if user:
                metadata["user"] = user
            if uid is not None:
                metadata["uid"] = uid
            if pid:
                metadata["pid"] = pid
            if hostname:
                metadata["hostname"] = hostname

            return ParsedLogEvent(
                event_type=LinuxEventType.SESSION_OPENED.value,
                event_group=EventGroup.SESSION.value,
                component=component,
                template="session opened for user <*> by LOGIN(uid=<*>)",
                template_id=103,  # E103 (custom)
                timestamp=timestamp,
                status="success",
                metadata=metadata,
                raw_message=message
            ).to_dict()

        elif "session closed" in message:
            match = self.SESSION_CLOSED.search(message)
            user = match.group("user") if match else None

            metadata = {}
            if user:
                metadata["user"] = user
            if pid:
                metadata["pid"] = pid
            if hostname:
                metadata["hostname"] = hostname

            return ParsedLogEvent(
                event_type=LinuxEventType.SESSION_CLOSED.value,
                event_group=EventGroup.SESSION.value,
                component=component,
                template="session closed for user <*>",
                template_id=101,  # E101
                timestamp=timestamp,
                status="success",
                metadata=metadata,
                raw_message=message
            ).to_dict()

        else:
            return ParsedLogEvent.unknown_event(
                log_line, component, timestamp=timestamp
            ).to_dict()

    def _parse_ftp(self, message: str, component: str, pid: Optional[int],
                   hostname: str, timestamp: str, log_line: str) -> Dict[str, Any]:
        """Parse FTP events"""
        
        # FTP Connection
        if "connection from" in message and "at" in message:
            match = self.FTP_CONNECTION.search(message)
            if match:
                ip = match.group("ip")
                ftp_hostname = match.group("hostname")

                metadata = {
                    "ip": ip,
                    "hostname": ftp_hostname
                }
                if pid:
                    metadata["pid"] = pid

                return ParsedLogEvent(
                    event_type=LinuxEventType.FTP_CONNECT.value,
                    event_group=EventGroup.CONNECTION.value,
                    component=component,
                    template="connection from <*> (<*>) at <*>:<*>:<*>",
                    template_id=29,  # E29
                    timestamp=timestamp,
                    status="success",
                    metadata=metadata,
                    raw_message=message
                ).to_dict()

        # FTP Timeout
        elif "timed out after" in message:
            match = self.FTP_TIMEOUT.search(message)
            if match:
                user = match.group("user") if match.group("user") != "unknown" else "anonymous"
                duration = int(match.group("duration")) if match.group("duration") else None

                metadata = {"user": user}
                if duration:
                    metadata["duration"] = duration
                if pid:
                    metadata["pid"] = pid

                return ParsedLogEvent(
                    event_type=LinuxEventType.FTP_TIMEOUT.value,
                    event_group=EventGroup.CONNECTION.value,
                    component=component,
                    template="User <*> timed out after <*> seconds",
                    template_id=112,  # Custom (not in CSV)
                    timestamp=timestamp,
                    status="timeout",
                    metadata=metadata,
                    raw_message=message
                ).to_dict()

        # FTP Anonymous Login
        elif "ANONYMOUS FTP LOGIN" in message:
            match = self.FTP_LOGIN.search(message)
            if match:
                ip = match.group("ip")

                metadata = {
                    "ip": ip,
                    "user": "anonymous"
                }
                if pid:
                    metadata["pid"] = pid

                return ParsedLogEvent(
                    event_type=LinuxEventType.FTP_LOGIN.value,
                    event_group=EventGroup.CONNECTION.value,
                    component=component,
                    template="ANONYMOUS FTP LOGIN FROM <*>,  (anonymous)",
                    template_id=9,  # E9
                    timestamp=timestamp,
                    status="success",
                    metadata=metadata,
                    raw_message=message
                ).to_dict()

        # Generic FTP event
        return ParsedLogEvent(
            event_type=LinuxEventType.FTP_EVENT.value,
            event_group=EventGroup.CONNECTION.value,
            component=component,
            template="",
            template_id=0,
            timestamp=timestamp,
            status="unknown",
            metadata={"pid": pid} if pid else {},
            raw_message=message,
            parsed_successfully=False,
            confidence=0.5
        ).to_dict()

    def _parse_logrotate(self, message: str, component: str,
                        hostname: str, timestamp: str, log_line: str) -> Dict[str, Any]:
        """Parse logrotate alerts"""
        
        if "ALERT exited abnormally" in message:
            match = self.ALERT_PATTERN.search(message)
            exit_code = int(match.group("exit_code")) if match else None

            metadata = {}
            if exit_code is not None:
                metadata["exit_code"] = exit_code
            if hostname:
                metadata["hostname"] = hostname

            return ParsedLogEvent(
                event_type=LinuxEventType.ALERT_ERROR.value,
                event_group=EventGroup.ERROR.value,
                component=component,
                template="ALERT exited abnormally with [<*>]",
                template_id=8,  # E8
                timestamp=timestamp,
                status="failure",
                metadata=metadata,
                raw_message=message
            ).to_dict()

        return ParsedLogEvent(
            event_type=LinuxEventType.UNKNOWN.value,
            event_group=EventGroup.SYSTEM.value,
            component=component,
            template="",
            template_id=0,
            timestamp=timestamp,
            status="unknown",
            metadata={},
            raw_message=message,
            parsed_successfully=False
        ).to_dict()

    def _parse_kernel(self, message: str, component: str,
                     hostname: str, timestamp: str, log_line: str) -> Dict[str, Any]:
        """Parse kernel messages (low anomaly value)"""
        
        return ParsedLogEvent(
            event_type=LinuxEventType.SYSTEM_INFO.value,
            event_group=EventGroup.SYSTEM.value,
            component=component,
            template="",
            template_id=0,
            timestamp=timestamp,
            status="info",
            metadata={"hostname": hostname} if hostname else {},
            raw_message=message,
            parsed_successfully=True,
            confidence=0.7
        ).to_dict()

    def _parse_generic(self, component: str, message: str, pid: Optional[int],
                      hostname: str, timestamp: str, log_line: str) -> Dict[str, Any]:
        """Generic fallback parser for unknown components"""
        
        # Try to extract basic patterns
        user_match = re.search(r"(?:user|for)\s+(\w+)", message)
        user = user_match.group(1) if user_match else None

        ip_match = re.search(r"(?:from|rhost=)\s*([\d.]+)", message)
        ip = ip_match.group(1) if ip_match else None

        metadata = {}
        if user:
            metadata["user"] = user
        if ip:
            metadata["ip"] = ip
        if pid:
            metadata["pid"] = pid
        if hostname:
            metadata["hostname"] = hostname

        return ParsedLogEvent(
            event_type=LinuxEventType.UNKNOWN.value,
            event_group=EventGroup.SYSTEM.value,
            component=component,
            template="",
            template_id=0,
            timestamp=timestamp,
            status="unknown",
            metadata=metadata,
            raw_message=message,
            parsed_successfully=False,
            confidence=0.3
        ).to_dict()

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def _parse_timestamp(self, month_str: str, day_str: str, time_str: str) -> Optional[str]:
        """
        Parse Linux syslog timestamp (missing year) into ISO 8601 format.
        
        Args:
            month_str: Month name (Jan, Feb, etc)
            day_str: Day of month (1-31)
            time_str: Time in HH:MM:SS format
            
        Returns:
            ISO 8601 timestamp string (YYYY-MM-DDTHH:MM:SS), or None if parse fails
        """
        try:
            month_num = self.MONTH_MAP.get(month_str)
            if not month_num:
                return None

            day_num = int(day_str)
            
            # Parse time
            dt = datetime.strptime(
                f"{self.context_year} {month_num} {day_num} {time_str}",
                "%Y %m %d %H:%M:%S"
            )
            
            return dt.isoformat()
        except (ValueError, TypeError):
            return None

    def _parse_component(self, component_full: str) -> tuple:
        """
        Parse component string into main component and subcomponent.
        
        Examples:
            "sshd(pam_unix)" -> ("sshd", "pam_unix")
            "ftpd" -> ("ftpd", None)
        """
        if "(" in component_full:
            parts = component_full.split("(")
            component = parts[0]
            subcomponent = parts[1].rstrip(")")
            return component, subcomponent
        return component_full, None

    def _build_unknown_event(self, log_line: str, error: str = "") -> Dict[str, Any]:
        """Handle unparseable logs"""
        event = ParsedLogEvent.unknown_event(
            log_line=log_line,
            component="unknown",
            error=error or "Could not parse log line"
        )
        return event.to_dict()
