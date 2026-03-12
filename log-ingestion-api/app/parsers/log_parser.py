import re
from typing import Dict

class LogParser:
    """
    Basic log parser for extracting structured data from raw log messages.
    """
    login_pattern = re.compile(r"User (?P<user>\w+) logged in from (?P<ip>[\d\.]+)")
    error_pattern = re.compile(r"Service (?P<service>\w+) failed with error (?P<error>.+)")

    def parse(self, message: str) -> Dict:
        """
        Parse raw log message into structured fields
        """
        login_match = self.login_pattern.search(message)
        if login_match:
            return {
                "event_type": "login",
                "user": login_match.group("user"),
                "ip": login_match.group("ip")
            }
        
        error_match = self.error_pattern.search(message)
        if error_match:
            return {
                "event_type": "service_error",
                "service": error_match.group("service"),
                "error": error_match.group("error")
            }
        
        return {"event_type": "unknown"}