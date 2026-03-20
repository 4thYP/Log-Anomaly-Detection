from app.parsers.base_parser import BaseParser

class WindowsParser(BaseParser):
    def parse(self, message: str):
        return {
            "event_type": "windows_event",
            "template": message
        }
