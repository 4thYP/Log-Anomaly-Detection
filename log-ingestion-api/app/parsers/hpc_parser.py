from app.parsers.base_parser import BaseParser

class HPCParser(BaseParser):
    def parse(self, message: str):
        return {
            "event_type": "hpc_event",
            "template": message
        }
