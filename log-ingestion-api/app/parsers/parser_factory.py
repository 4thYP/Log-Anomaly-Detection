from app.models.log_models import ServerType
from app.parsers.linux_parser import LinuxParser
from app.parsers.hpc_parser import HPCParser
from app.parsers.healthapp_parser import HealthAppParser
from app.parsers.windows_parser import WindowsParser
from app.parsers.zookeeper_parser import ZookeeperParser

class ParserFactory:

    @staticmethod
    def get_parser(server_type: ServerType):

        if server_type == ServerType.LINUX:
            return LinuxParser()

        elif server_type == ServerType.HPC:
            return HPCParser()

        elif server_type == ServerType.HEALTHAPP:
            return HealthAppParser()

        elif server_type == ServerType.WINDOWS:
            return WindowsParser()

        elif server_type == ServerType.ZOOKEEPER:
            return ZookeeperParser()

        else:
            raise ValueError(f"No parser for server type: {server_type}")
