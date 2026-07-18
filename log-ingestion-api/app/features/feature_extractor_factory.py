from app.models.log_models import ServerType
from app.features.linux_feature_extractor import LinuxFeatureExtractor
from app.features.windows_feature_extractor import WindowsFeatureExtractor 
from app.features.zookeeper_feature_extractor import ZookeeperFeatureExtractor
from app.features.hpc_feature_extractor import HPCFeatureExtractor
from app.features.healthapp_feature_extractor import HealthAppFeatureExtractor

class FeatureExtractorFactory:
    _instances = {}

    @classmethod
    def get_extractor(cls, server_type: ServerType):
        # Reuse instances (stateful per-server internally)
        if server_type not in cls._instances:
            if server_type == ServerType.LINUX:
                cls._instances[server_type] = LinuxFeatureExtractor()
            elif server_type == ServerType.WINDOWS:
                cls._instances[server_type] = WindowsFeatureExtractor()
            elif server_type == ServerType.ZOOKEEPER:
                cls._instances[server_type] = ZookeeperFeatureExtractor()
            elif server_type == ServerType.HPC:
                cls._instances[server_type] = HPCFeatureExtractor()
            elif server_type == ServerType.HEALTHAPP:
                cls._instances[server_type] = HealthAppFeatureExtractor()
            else:
                raise ValueError(f"No feature extractor for {server_type}")
        
        return cls._instances[server_type]
