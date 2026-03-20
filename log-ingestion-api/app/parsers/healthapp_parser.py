from app.parsers.base_parser import BaseParser

class HealthAppParser(BaseParser):
    def parse(self, message: str):
        return {
            "event_type": "healthapp_event",
            "template": message
        }
