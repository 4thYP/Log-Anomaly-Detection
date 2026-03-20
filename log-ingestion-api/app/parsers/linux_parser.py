import re
from typing import Dict
from app.parsers.base_parser import BaseParser


class LinuxParser(BaseParser):

    # ===== HEADER PATTERN =====
    header_pattern = re.compile(
        r"^(?P<month>\w+) (?P<day>\d+) (?P<time>\d+:\d+:\d+) "
        r"(?P<host>\S+) (?P<process>[^\[]+)\[(?P<pid>\d+)\]: (?P<message>.*)"
    )

    # ===== EVENT PATTERNS =====

    auth_failure_pattern = re.compile(
        r"authentication failure;.*rhost=(?P<ip>[\w\.\-]+).*?(user=(?P<user>\w+))?"
    )

    invalid_user_pattern = re.compile(
        r"check pass; user unknown"
    )

    session_open_pattern = re.compile(
        r"session opened for user (?P<user>\w+)"
    )

    session_close_pattern = re.compile(
        r"session closed for user (?P<user>\w+)"
    )

    ftp_connection_pattern = re.compile(
        r"connection from (?P<ip>[\d\.]+)"
    )

    logrotate_alert_pattern = re.compile(
        r"logrotate: ALERT"
    )

    def parse(self, message: str) -> Dict:

        # ===== STEP 1: Parse header =====
        header_match = self.header_pattern.match(message)

        if not header_match:
            return {
                "event_type": "unknown",
                "template": "unknown"
            }

        header = header_match.groupdict()
        msg = header["message"]

        process = header["process"].strip()

        # ===== STEP 2: Detect event type =====

        # AUTH FAILURE
        match = self.auth_failure_pattern.search(msg)
        if match:
            return {
                "event_type": "auth_failure",
                "process": process,
                "ip": match.group("ip"),
                "user": match.group("user"),
                "status": "failed",
                "template": "authentication failure from <*> user <*>"
            }

        # INVALID USER
        if self.invalid_user_pattern.search(msg):
            return {
                "event_type": "invalid_user",
                "process": process,
                "status": "failed",
                "template": "check pass user unknown"
            }

        # SESSION OPEN
        match = self.session_open_pattern.search(msg)
        if match:
            return {
                "event_type": "session_open",
                "process": process,
                "user": match.group("user"),
                "status": "success",
                "template": "session opened for user <*>"
            }

        # SESSION CLOSE
        match = self.session_close_pattern.search(msg)
        if match:
            return {
                "event_type": "session_close",
                "process": process,
                "user": match.group("user"),
                "status": "success",
                "template": "session closed for user <*>"
            }

        # FTP CONNECTION
        match = self.ftp_connection_pattern.search(msg)
        if match:
            return {
                "event_type": "ftp_connection",
                "process": process,
                "ip": match.group("ip"),
                "template": "ftp connection from <*>"
            }

        # LOGROTATE ALERT
        if self.logrotate_alert_pattern.search(msg):
            return {
                "event_type": "system_alert",
                "process": process,
                "template": "logrotate alert"
            }

        # DEFAULT
        return {
            "event_type": "other",
            "process": process,
            "template": msg[:50]
        }
