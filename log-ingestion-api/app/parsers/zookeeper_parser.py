from app.parsers.base_parser import BaseParser

class ZookeeperParser(BaseParser):
    def parse(self, message: str):
        return {
            "event_type": "zookeeper_event",
            "template": message
        }
