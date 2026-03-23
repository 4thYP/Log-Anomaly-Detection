"""
Production-grade Linux log parser for Loghub Linux logs.
Handles SSH, FTP, session, and system events with robust regex patterns.
"""

import re
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from app.parsers.base_parser import BaseParser


@dataclass
class ParsedLogEvent:
    """Unified schema for all Linux log events"""
    event_type: str
    component: str
    template_id: Optional[str] = None
    template: str = ""
    user: Optional[str] = None
    ip: Optional[str] = None
    hostname: Optional[str] = None
    status: Optional[str] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    uid: Optional[int] = None
    pid: Optional[int] = None
    duration: Optional[int] = None
    attempt_count: Optional[int] = None
    raw_message: str = ""
    parsed_successfully: bool = True
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class LinuxParser(BaseParser):
    """
    Parser for Linux syslog entries from Loghub dataset.
    
    Handles:
    - SSH authentication events (sshd with pam_unix)
    - Session management (su, login)
    - FTP connection events
    - System alerts and services
    - Kernel boot messages
    """

    # ============================================================================
    # REGEX PATTERNS - Production-grade with named groups
    # ============================================================================

    # Header pattern: "Mon DD HH:MM:SS"
    HEADER_PATTERN = re.compile(
        r"^(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})\s+"
        r"(?P<host>\S+)\s+(?P<component_full>\S+?)(?:\[(?P<pid>\d+)\])?: (?P<message>.*)"
    )

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
        r"User (?P<user>\S+) timed out after (?P<duration>\d+) seconds at (?P<timestamp>.*)"
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

    # Kernel/System info patterns (low anomaly value - often noise)
    KERNEL_INFO = re.compile(
        r"(?:Linux version|Memory:|kernel core_uses_pid|dmesg)"
    )

    # ============================================================================
    # PARSER IMPLEMENTATION
    # ============================================================================

    def parse(self, log_line: str) -> Dict[str, Any]:
        """
        Parse a single Linux syslog line.

        Args:
            log_line: Raw syslog line

        Returns:
            Dictionary with parsed event in standardized format
        """
        try:
            # Parse header
            header_match = self.HEADER_PATTERN.match(log_line)
            if not header_match:
                return self._unknown_log(log_line)

            groups = header_match.groupdict()
            component_full = groups.get("component_full", "")
            message = groups.get("message", "")
            pid = groups.get("pid")

            # Parse component and subcomponent (e.g., sshd(pam_unix) -> sshd, pam_unix)
            component, subcomponent = self._parse_component(component_full)

            # Convert PID to int if present
            pid_int = int(pid) if pid else None

            # Route to appropriate parser based on component
            if component == "sshd":
                return self._parse_ssh(message, component, pid_int, log_line)
            elif component == "su":
                return self._parse_session_su(message, component, pid_int, log_line)
            elif component == "login":
                return self._parse_session_login(message, component, pid_int, log_line)
            elif component == "ftpd":
                return self._parse_ftp(message, component, pid_int, log_line)
            elif component == "logrotate":
                return self._parse_logrotate(message, component, log_line)
            elif component == "kernel":
                return self._parse_kernel(message, component, log_line)
            else:
                # Try generic parsing
                return self._parse_generic(component, message, pid_int, log_line)

        except Exception as e:
            return self._unknown_log(log_line, str(e))

    # ============================================================================
    # COMPONENT PARSERS
    # ============================================================================

    def _parse_ssh(self, message: str, component: str, pid: Optional[int], 
                   log_line: str) -> Dict[str, Any]:
        """Parse SSH (sshd) authentication events"""
        
        # Check for authentication failure
        if "authentication failure" in message:
            match = self.SSH_AUTH_FAILURE.search(message)
            ip = match.group("ip") if match and match.group("ip") else None
            user = match.group("user") if match and match.group("user") else None

            # Determine template based on user presence
            if user:
                if user == "root":
                    template_id = "E18"
                    template = "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*>  user=root"
                elif user == "test":
                    template_id = "E19"
                    template = "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*>  user=test"
                elif user == "guest":
                    template_id = "E17"
                    template = "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*>  user=guest"
                else:
                    template_id = "E16"
                    template = "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*>"
            else:
                template_id = "E16"
                template = "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*>"

            return self._build_event(
                event_type="auth_failure",
                component=component,
                template_id=template_id,
                template=template,
                user=user,
                ip=ip,
                status="failure",
                pid=pid,
                raw_message=message,
                uid=0
            )

        # Check for "check pass; user unknown"
        elif self.SSH_CHECK_PASS.search(message):
            return self._build_event(
                event_type="auth_check",
                component=component,
                template_id="E27",
                template="check pass; user unknown",
                status="check_pass",
                pid=pid,
                raw_message=message
            )

        # Fallback for other SSH messages
        else:
            return self._build_event(
                event_type="ssh_event",
                component=component,
                status="unknown",
                pid=pid,
                raw_message=message,
                parsed_successfully=False,
                confidence=0.5
            )

    def _parse_session_su(self, message: str, component: str, pid: Optional[int],
                         log_line: str) -> Dict[str, Any]:
        """Parse session events from su (substitute user)"""
        
        # Session opened
        if "session opened" in message:
            match = self.SESSION_OPENED.search(message)
            user = match.group("user") if match else None
            uid = int(match.group("uid")) if match and match.group("uid") else None

            return self._build_event(
                event_type="session_opened",
                component=component,
                template_id="E102",
                template="session opened for user <*> by (uid=<*>)",
                user=user,
                status="success",
                uid=uid,
                pid=pid,
                raw_message=message
            )

        # Session closed
        elif "session closed" in message:
            match = self.SESSION_CLOSED.search(message)
            user = match.group("user") if match else None

            return self._build_event(
                event_type="session_closed",
                component=component,
                template_id="E101",
                template="session closed for user <*>",
                user=user,
                status="closed",
                pid=pid,
                raw_message=message
            )

        else:
            return self._build_event(
                event_type="session_event",
                component=component,
                status="unknown",
                pid=pid,
                raw_message=message,
                parsed_successfully=False
            )

    def _parse_session_login(self, message: str, component: str, pid: Optional[int],
                            log_line: str) -> Dict[str, Any]:
        """Parse login session events"""
        
        # Similar to su, but for login
        if "session opened" in message:
            match = self.SESSION_OPENED.search(message)
            user = match.group("user") if match else None
            uid = int(match.group("uid")) if match and match.group("uid") else None

            return self._build_event(
                event_type="session_opened",
                component=component,
                template_id="E103",
                template="session opened for user <*> by LOGIN(uid=<*>)",
                user=user,
                status="success",
                uid=uid,
                pid=pid,
                raw_message=message
            )
        elif "session closed" in message:
            match = self.SESSION_CLOSED.search(message)
            user = match.group("user") if match else None

            return self._build_event(
                event_type="session_closed",
                component=component,
                template_id="E101",
                template="session closed for user <*>",
                user=user,
                status="closed",
                pid=pid,
                raw_message=message
            )
        else:
            return self._build_event(
                event_type="session_event",
                component=component,
                raw_message=message,
                parsed_successfully=False
            )

    def _parse_ftp(self, message: str, component: str, pid: Optional[int],
                   log_line: str) -> Dict[str, Any]:
        """Parse FTP events"""
        
        # FTP Connection
        if "connection from" in message and "at" in message:
            match = self.FTP_CONNECTION.search(message)
            if match:
                ip = match.group("ip")
                hostname = match.group("hostname")
                
                return self._build_event(
                    event_type="ftp_connect",
                    component=component,
                    template_id="E29",
                    template="connection from <*> (<*>) at <*>:<*>:<*>",
                    ip=ip,
                    hostname=hostname,
                    status="connect",
                    pid=pid,
                    raw_message=message
                )

        # FTP Timeout
        elif "timed out after" in message:
            match = self.FTP_TIMEOUT.search(message)
            if match:
                user = match.group("user") if match.group("user") != "unknown" else "anonymous"
                duration = int(match.group("duration")) if match.group("duration") else None

                return self._build_event(
                    event_type="ftp_timeout",
                    component=component,
                    template_id="E112",
                    template="User unknown timed out after <*> seconds at <*>:<*>:<*> <*>",
                    user=user,
                    status="timeout",
                    duration=duration,
                    pid=pid,
                    raw_message=message
                )

        # FTP Anonymous Login
        elif "ANONYMOUS FTP LOGIN" in message:
            match = self.FTP_LOGIN.search(message)
            if match:
                ip = match.group("ip")
                email = match.group("email")

                return self._build_event(
                    event_type="ftp_login",
                    component=component,
                    template_id="E9",
                    template="ANONYMOUS FTP LOGIN FROM <*>,  (anonymous)",
                    ip=ip,
                    user="anonymous",
                    status="login",
                    pid=pid,
                    raw_message=message
                )

        # Generic FTP event
        return self._build_event(
            event_type="ftp_event",
            component=component,
            status="unknown",
            pid=pid,
            raw_message=message,
            parsed_successfully=False,
            confidence=0.5
        )

    def _parse_logrotate(self, message: str, component: str,
                        log_line: str) -> Dict[str, Any]:
        """Parse logrotate alerts"""
        
        if "ALERT exited abnormally" in message:
            match = self.ALERT_PATTERN.search(message)
            exit_code = int(match.group("exit_code")) if match else None

            return self._build_event(
                event_type="alert",
                component=component,
                template_id="E8",
                template="ALERT exited abnormally with [1]",
                status="abnormal_exit",
                exit_code=exit_code,
                raw_message=message
            )

        return self._build_event(
            event_type="logrotate_event",
            component=component,
            raw_message=message,
            parsed_successfully=False
        )

    def _parse_kernel(self, message: str, component: str,
                     log_line: str) -> Dict[str, Any]:
        """Parse kernel messages (low anomaly value)"""
        
        # Kernel messages are mostly boot/config info - skip detailed parsing
        # Classify as system_info to filter them out in anomaly detection
        return self._build_event(
            event_type="system_info",
            component=component,
            status="info",
            raw_message=message,
            parsed_successfully=True,
            confidence=0.7
        )

    def _parse_generic(self, component: str, message: str, pid: Optional[int],
                      log_line: str) -> Dict[str, Any]:
        """Generic fallback parser for unknown components"""
        
        # Try to extract basic patterns
        user_match = re.search(r"(?:user|for)\s+(\w+)", message)
        user = user_match.group(1) if user_match else None

        ip_match = re.search(r"(?:from|rhost=)\s*([\d.]+)", message)
        ip = ip_match.group(1) if ip_match else None

        return self._build_event(
            event_type="generic",
            component=component,
            user=user,
            ip=ip,
            pid=pid,
            raw_message=message,
            parsed_successfully=False,
            confidence=0.3
        )

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

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

    def _build_event(
        self,
        event_type: str,
        component: str,
        template_id: Optional[str] = None,
        template: str = "",
        user: Optional[str] = None,
        ip: Optional[str] = None,
        hostname: Optional[str] = None,
        status: Optional[str] = None,
        exit_code: Optional[int] = None,
        error_message: Optional[str] = None,
        uid: Optional[int] = None,
        pid: Optional[int] = None,
        duration: Optional[int] = None,
        raw_message: str = "",
        parsed_successfully: bool = True,
        confidence: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Build a standardized event dictionary.
        """
        event = ParsedLogEvent(
            event_type=event_type,
            component=component,
            template_id=template_id,
            template=template,
            user=user,
            ip=ip,
            hostname=hostname,
            status=status,
            exit_code=exit_code,
            error_message=error_message,
            uid=uid,
            pid=pid,
            duration=duration,
            raw_message=raw_message,
            parsed_successfully=parsed_successfully,
            confidence=confidence,
        )
        return event.to_dict()

    def _unknown_log(self, log_line: str, error: str = "") -> Dict[str, Any]:
        """Handle unparseable logs"""
        return ParsedLogEvent(
            event_type="unknown",
            component="unknown",
            status="parse_error",
            raw_message=log_line[:200],  # Truncate for storage
            parsed_successfully=False,
            confidence=0.0,
            error_message=error if error else "Could not match header pattern"
        ).to_dict()
