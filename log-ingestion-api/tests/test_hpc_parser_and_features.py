"""
HPC Parser and Feature Extractor Test Cases

This module demonstrates the complete pipeline:
Raw Log → Parsed Output → Feature Vector
"""

import pytest
from datetime import datetime
from app.models.log_models import LogCreate, ServerType
from app.parsers.hpc_parser import HPCParser
from app.features.hpc_feature_extractor import HPCFeatureExtractor
from app.parsers.log_event_schema import EventGroup


class TestHPCParserBasic:
    """Test HPC parser output format and schema compliance"""
    
    @pytest.fixture
    def parser(self):
        return HPCParser()
    
    def test_component_unavailable_event(self, parser):
        """Test E13: Component State Change (unavailable)"""
        raw_log = '134681 node-246 unix.hw state_change.unavailable 1077804742 1 Component State Change: Component \042SCSI-WWID:01000010:6005-08b4-0001-00c6-0006-3000-003d-0000\042 is in the unavailable state (HWID=1973)'
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "component_unavailable"
        assert parsed["event_group"] == EventGroup.ERROR
        assert parsed["component"] == "unix.hw"
        assert parsed["template_id"] == 13
        assert parsed["timestamp"] == "2004-02-26T14:12:22"  # Unix 1077804742 → UTC timestamp
        assert parsed["status"] == "unavailable"
        assert parsed["metadata"]["hwid"] == "1973"
        assert "SCSI-WWID" in parsed["metadata"]["component_name"]
        assert parsed["metadata"]["node"] == "node-246"
        assert parsed["metadata"]["log_id"] == "134681"
    
    def test_boot_action_event(self, parser):
        """Test E4: boot command"""
        raw_log = '2575909 node-162 action start 1074178193 1 boot  (command 1911)'
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "boot_started"
        assert parsed["event_group"] == EventGroup.SERVICE
        assert parsed["component"] == "action"
        assert parsed["template_id"] == 4
        assert parsed["timestamp"] == "2004-01-15T14:49:53"  # Unix 1074178193 → UTC timestamp
        assert parsed["status"] == "started"
        assert parsed["metadata"]["command_id"] == "1911"
        assert parsed["metadata"]["node"] == "node-162"
        assert parsed["metadata"]["action_type"] == "boot"
    
    def test_halt_action_event(self, parser):
        """Test E19: halt command"""
        raw_log = '2608062 node-238 action start 1074461014 1 halt  (command 1982)'
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "halt_started"
        assert parsed["event_group"] == EventGroup.SERVICE
        assert parsed["component"] == "action"
        assert parsed["template_id"] == 19
        assert parsed["status"] == "started"
        assert parsed["metadata"]["command_id"] == "1982"
        assert parsed["metadata"]["action_type"] == "halt"
    
    def test_wait_action_event(self, parser):
        """Test E45: wait command"""
        raw_log = '2601401 node-184 action start 1074298390 1 wait  (command 1975)'
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "wait_started"
        assert parsed["event_group"] == EventGroup.SERVICE
        assert parsed["template_id"] == 45
        assert parsed["metadata"]["command_id"] == "1975"
        assert parsed["metadata"]["action_type"] == "wait"
    
    def test_risboot_action_event(self, parser):
        """Test E36: risBoot command"""
        raw_log = '2571927 node-28 action start 1074125371 1 risBoot  (command 1903)'
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "risboot_started"
        assert parsed["event_group"] == EventGroup.SERVICE
        assert parsed["template_id"] == 36
        assert parsed["metadata"]["command_id"] == "1903"
    
    def test_bootvmunix_action_event(self, parser):
        """Test E6: bootGenvmunix command"""
        raw_log = '2572286 node-17 action start 1074126278 1 bootGenvmunix  (command 1903)'
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "bootvmunix_started"
        assert parsed["event_group"] == EventGroup.SERVICE
        assert parsed["template_id"] == 6
        assert parsed["metadata"]["command_id"] == "1903"
    
    def test_cluster_add_member_event(self, parser):
        """Test E8: clusterAddMember command"""
        raw_log = '2568643 node-70 action start 1074119817 1 clusterAddMember  (command 1902)'
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "cluster_add_member"
        assert parsed["event_group"] == EventGroup.SERVICE
        assert parsed["template_id"] == 8
        assert parsed["metadata"]["command_id"] == "1902"
    
    def test_component_active_event(self, parser):
        """Test E1: Component active state"""
        raw_log = '100001 node-100 unix.hw state_change.active 1074200000 1 active'
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "component_active"
        assert parsed["event_group"] == EventGroup.SYSTEM
        assert parsed["template_id"] == 1
        assert parsed["status"] == "active"
    
    def test_component_critical_event(self, parser):
        """Test E15: Component critical state"""
        raw_log = '100002 node-101 unix.hw state_change.critical 1074210000 1 critical'
        
        parsed = parser.parse(raw_log)
        
        assert parsed["event_type"] == "component_critical"
        assert parsed["event_group"] == EventGroup.ERROR
        assert parsed["template_id"] == 15
        assert parsed["status"] == "critical"
    
    def test_malformed_log_returns_unknown(self, parser):
        """Test malformed/unparseable log returns unknown event"""
        raw_log = 'this is not a valid hpc log format @#$%'
        
        parsed = parser.parse(raw_log)
        
        # Should fail to parse due to too few fields
        assert parsed["event_type"] == "unknown"
        assert parsed["event_group"] == EventGroup.SYSTEM
        assert parsed["metadata"]["parsed_successfully"] is False


class TestHPCFeatureExtractor:
    """Test feature extraction and output format"""
    
    @pytest.fixture
    def extractor(self):
        return HPCFeatureExtractor()
    
    @pytest.fixture
    def parser(self):
        return HPCParser()
    
    def create_log_internal(self, sid, raw_log):
        """Helper to create LogInternal with parsed data"""
        from app.models.log_models import LogInternal
        from datetime import datetime
        
        parser = HPCParser()
        parsed_data = parser.parse(raw_log)
        
        log_internal = LogInternal(
            sid=sid,
            timestamp=datetime.utcnow(),
            server_type=ServerType.HPC,
            log_file="test.log",
            message=raw_log,
            metadata={"parsed": parsed_data}
        )
        return log_internal
    
    def test_feature_vector_format(self, extractor):
        """Test feature output is List[float], not Dict"""
        log = self.create_log_internal(
            "hpc-001",
            '2575909 node-162 action start 1074178193 1 boot  (command 1911)'
        )
        
        features = extractor.extract(log)
        
        # Check type and length
        assert isinstance(features, list)
        assert len(features) == 13
        assert all(isinstance(f, float) for f in features)
    
    def test_all_features_normalized_01(self, extractor):
        """Test all features are normalized to [0, 1]"""
        log = self.create_log_internal(
            "hpc-001",
            '2575909 node-162 action start 1074178193 1 boot  (command 1911)'
        )
        
        features = extractor.extract(log)
        
        # All values should be in [0, 1]
        assert all(0.0 <= f <= 1.0 for f in features)
    
    def test_per_server_isolation(self, extractor):
        """Test feature extraction maintains state per server (sid)"""
        # Server 1: boot event
        log1a = self.create_log_internal(
            "hpc-server-1",
            '2575909 node-162 action start 1074178193 1 boot  (command 1911)'
        )
        features1a = extractor.extract(log1a)
        
        # Server 2: error event
        log2a = self.create_log_internal(
            "hpc-server-2",
            '134681 node-246 unix.hw state_change.unavailable 1077804742 1 Component State Change: Component \042alt0\042 is in the unavailable state (HWID=1973)'
        )
        features2a = extractor.extract(log2a)
        
        # Server 1: another boot event
        log1b = self.create_log_internal(
            "hpc-server-1",
            '2600743 node-57 action start 1074298084 1 boot  (command 1967)'
        )
        features1b = extractor.extract(log1b)
        
        # Server 1 features should evolve independently from Server 2
        # (boot rate accumulates for server-1, not affected by error in server-2)
        assert features1a != features1b  # Different due to accumulated state
        assert extractor.server_states["hpc-server-1"].group_counts[EventGroup.SERVICE] >= 2
        assert extractor.server_states["hpc-server-2"].group_counts[EventGroup.ERROR] >= 1
    
    def test_error_rate_calculation(self, extractor):
        """Test error_rate feature reflects ERROR group events"""
        # All error events
        log1 = self.create_log_internal(
            "hpc-002",
            '134681 node-246 unix.hw state_change.unavailable 1077804742 1 Component State Change: Component \042alt0\042 is in the unavailable state (HWID=1973)'
        )
        features1 = extractor.extract(log1)
        error_rate_1 = features1[1]  # Index 1 is error_rate
        
        # Add service event
        log2 = self.create_log_internal(
            "hpc-002",
            '2575909 node-162 action start 1074178193 1 boot  (command 1911)'
        )
        features2 = extractor.extract(log2)
        error_rate_2 = features2[1]
        
        # Error rate should decrease after adding service event
        assert error_rate_2 < error_rate_1
    
    def test_boots_vs_halts_differentiation(self, extractor):
        """Test boot_frequency and halt_frequency track separately"""
        # Boot events (3x)
        for i in range(3):
            log = self.create_log_internal(
                "hpc-003",
                '2575909 node-162 action start 1074178193 1 boot  (command 1911)'
            )
            features = extractor.extract(log)
        boot_freq_after_boots = features[7]
        
        # Halt events (1x)
        log = self.create_log_internal(
            "hpc-003",
            '2608062 node-238 action start 1074461014 1 halt  (command 1982)'
        )
        features = extractor.extract(log)
        boot_freq_after_halt = features[7]
        halt_freq_after_halt = features[8]
        
        # After halt, boot ratio should decrease (now 3 boots out of 4 total)
        # Halt should have at least some contribution
        assert boot_freq_after_halt < boot_freq_after_boots  # Boot rate decreased
        assert halt_freq_after_halt > 0  # Halt freq now > 0


class TestHPCPipelineIntegration:
    """Test end-to-end pipeline: LogCreate → Parse → Extract"""
    
    def test_full_pipeline_single_log(self):
        """Test complete pipeline for single log"""
        from app.models.log_models import LogInternal, LogCreate
        from datetime import datetime
        from app.parsers.parser_factory import ParserFactory
        from app.features.feature_extractor_factory import FeatureExtractorFactory
        
        # Create log
        raw_log = '2575909 node-162 action start 1074178193 1 boot  (command 1911)'
        
        log_create = LogCreate(
            sid="hpc-cluster-001",
            timestamp=datetime.utcfromtimestamp(1074178193),
            server_type=ServerType.HPC,
            log_file="hpc_cluster.log",
            message=raw_log,
        )
        
        # Convert to internal
        log_internal = LogInternal(**log_create.model_dump())
        
        # Parse
        parser = ParserFactory.get_parser(ServerType.HPC)
        parsed_data = parser.parse(raw_log)
        log_internal.metadata = {"parsed": parsed_data}
        
        # Extract features
        extractor = FeatureExtractorFactory.get_extractor(ServerType.HPC)
        features = extractor.extract(log_internal)
        
        # Verify end-to-end
        assert len(features) == 13
        assert all(0.0 <= f <= 1.0 for f in features)
        assert log_internal.metadata["parsed"]["event_type"] == "boot_started"
    
    def test_multi_server_processing(self):
        """Test processing multiple servers concurrently"""
        from app.models.log_models import LogInternal, LogCreate
        from datetime import datetime
        from app.parsers.parser_factory import ParserFactory
        from app.features.feature_extractor_factory import FeatureExtractorFactory
        
        parser = ParserFactory.get_parser(ServerType.HPC)
        extractor = FeatureExtractorFactory.get_extractor(ServerType.HPC)
        
        # Server 1 logs
        server1_logs = [
            '2575909 node-162 action start 1074178193 1 boot  (command 1911)',
            '2600743 node-57 action start 1074298084 1 boot  (command 1967)',
            '2608062 node-238 action start 1074461014 1 halt  (command 1982)',
        ]
        
        # Server 2 logs
        server2_logs = [
            '134681 node-246 unix.hw state_change.unavailable 1077804742 1 Component State Change: Component \042alt0\042 is in the unavailable state (HWID=1973)',
            '350766 node-109 unix.hw state_change.unavailable 1084680778 1 Component State Change: Component \042alt0\042 is in the unavailable state (HWID=3180)',
        ]
        
        features_s1 = []
        features_s2 = []
        
        for raw_log in server1_logs:
            log_internal = LogInternal(
                sid="server-1",
                timestamp=datetime.utcnow(),
                server_type=ServerType.HPC,
                log_file="test.log",
                message=raw_log,
                metadata={"parsed": parser.parse(raw_log)}
            )
            features_s1.append(extractor.extract(log_internal))
        
        for raw_log in server2_logs:
            log_internal = LogInternal(
                sid="server-2",
                timestamp=datetime.utcnow(),
                server_type=ServerType.HPC,
                log_file="test.log",
                message=raw_log,
                metadata={"parsed": parser.parse(raw_log)}
            )
            features_s2.append(extractor.extract(log_internal))
        
        # Server 1 should have higher service rate (3 boots + halts)
        service_rate_s1 = features_s1[-1][2]  # service_action_rate
        service_rate_s2 = features_s2[-1][2]
        
        # Server 2 should have higher error rate
        error_rate_s1 = features_s1[-1][1]
        error_rate_s2 = features_s2[-1][1]
        
        assert service_rate_s1 > service_rate_s2
        assert error_rate_s2 > error_rate_s1


class TestHPCEdgeCases:
    """Test edge cases and robustness"""
    
    @pytest.fixture
    def parser(self):
        return HPCParser()
    
    def test_escaped_quote_handling(self, parser):
        """Test unescaping of octal-encoded quotes in component names"""
        raw_log = '134681 node-246 unix.hw state_change.unavailable 1077804742 1 Component State Change: Component \042SCSI-WWID:01000010:6005-08b4-0001-00c6-0006-3000-003d-0000\042 is in the unavailable state (HWID=1973)'
        
        parsed = parser.parse(raw_log)
        
        # Component name should have quotes unescaped
        component_name = parsed["metadata"]["component_name"]
        assert '"' in component_name or "SCSI" in component_name
        assert "\042" not in component_name
    
    def test_missing_timestamp_handling(self, parser):
        """Test graceful handling of malformed timestamp"""
        raw_log = '999 node-100 unix.hw state_change.invalid notanumber 1 someinvalidmessage'
        
        parsed = parser.parse(raw_log)
        
        # Should return unknown event without crashing
        assert parsed["event_type"] == "unknown"
        assert parsed["metadata"]["parsed_successfully"] is False
    
    def test_large_command_ids(self, parser):
        """Test handling of large command ID values"""
        raw_log = '2575909 node-162 action start 1074178193 1 boot  (command 999999)'
        
        parsed = parser.parse(raw_log)
        
        assert parsed["metadata"]["command_id"] == "999999"
    
    def test_special_characters_in_component_names(self, parser):
        """Test component names with special chars like colons and hyphens"""
        raw_log = '134681 node-246 unix.hw state_change.unavailable 1077804742 1 Component State Change: Component \042SCSI-WWID:01000010:6005-08b4:0001:00c6\042 is in the unavailable state (HWID=1973)'
        
        parsed = parser.parse(raw_log)
        
        # Should extract complex component names without error
        assert "SCSI" in parsed["metadata"]["component_name"]


# ============================================================================
# EXAMPLE TEST DATA - Complete Examples with Raw, Parsed, and Features
# ============================================================================

EXAMPLE_1 = {
    "name": "Hardware Component Unavailable",
    "raw_log": '134681 node-246 unix.hw state_change.unavailable 1077804742 1 Component State Change: Component \042SCSI-WWID:01000010:6005-08b4-0001-00c6-0006-3000-003d-0000\042 is in the unavailable state (HWID=1973)',
    "expected_parsed": {
        "event_type": "component_unavailable",
        "event_group": "error",
        "component": "unix.hw",
        "template": "Component State Change: Component <*> is in the unavailable state (HWID=<*>)",
        "template_id": 13,
        "timestamp": "2004-02-26T10:39:02",
        "status": "unavailable",
        "metadata_keys": ["hwid", "component_name", "node", "log_id"],
    },
    "expected_features_summary": {
        "error_rate": "> 0.5",  # Error event
        "hardware_failure_ratio": "> 0.5",  # Unavailable = failure
        "service_action_rate": "0.0",  # No service events
    }
}

EXAMPLE_2 = {
    "name": "Boot Action Started",
    "raw_log": '2575909 node-162 action start 1074178193 1 boot  (command 1911)',
    "expected_parsed": {
        "event_type": "boot_started",
        "event_group": "service",
        "component": "action",
        "template": "boot  (command <*>)",
        "template_id": 4,
        "timestamp": "2004-01-15T14:49:53",  # Unix 1074178193 → UTC
        "status": "started",
        "metadata_keys": ["command_id", "node", "action_type"],
    },
    "expected_features_summary": {
        "error_rate": "0.0",  # Not an error
        "service_action_rate": "> 0.5",  # Service event
        "boot_action_frequency": "> 0.5",  # Boot event
    }
}

EXAMPLE_3 = {
    "name": "Halt Action Started",
    "raw_log": '2608062 node-238 action start 1074461014 1 halt  (command 1982)',
    "expected_parsed": {
        "event_type": "halt_started",
        "event_group": "service",
        "component": "action",
        "template": "halt  (command <*>)",
        "template_id": 19,
        "timestamp": "2004-01-18T10:43:34",  # Unix 1074461014 → UTC
        "status": "started",
    },
}

EXAMPLE_4 = {
    "name": "Component Active State",
    "raw_log": '100001 node-100 unix.hw state_change.active 1074200000 1 active',
    "expected_parsed": {
        "event_type": "component_active",
        "event_group": "system",
        "component": "unix.hw",
        "template": "active",
        "template_id": 1,
        "status": "active",
    },
}

EXAMPLE_5 = {
    "name": "Component Critical State",
    "raw_log": '100002 node-101 unix.hw state_change.critical 1074210000 1 critical',
    "expected_parsed": {
        "event_type": "component_critical",
        "event_group": "error",
        "component": "unix.hw",
        "template": "critical",
        "template_id": 15,
        "status": "critical",
    },
}

EXAMPLE_6 = {
    "name": "Cluster Add Member",
    "raw_log": '2568643 node-70 action start 1074119817 1 clusterAddMember  (command 1902)',
    "expected_parsed": {
        "event_type": "cluster_add_member",
        "event_group": "service",
        "component": "action",
        "template": "clusterAddMember  (command <*>)",
        "template_id": 8,
        "timestamp": "2004-01-15T10:03:37",  # Unix 1074119817 → UTC
        "status": "started",
    },
}


if __name__ == "__main__":
    # Example usage for manual testing
    print("=== HPC Test Examples ===\n")
    
    parser = HPCParser()
    extractor = HPCFeatureExtractor()
    
    for example in [EXAMPLE_1, EXAMPLE_2, EXAMPLE_3, EXAMPLE_4, EXAMPLE_5, EXAMPLE_6]:
        print(f"\n{example['name']}")
        print(f"Raw: {example['raw_log']}\n")
        
        parsed = parser.parse(example['raw_log'])
        print(f"Parsed event_type: {parsed['event_type']}, group: {parsed['event_group']}")
        print(f"Template ID: {parsed['template_id']}, Status: {parsed['status']}")
        
        # Create LogInternal for feature extraction
        from app.models.log_models import LogInternal
        from datetime import datetime
        
        log = LogInternal(
            sid="test-server",
            timestamp=datetime.utcnow(),
            server_type=ServerType.HPC,
            log_file="test.log",
            message=example['raw_log'],
            metadata={"parsed": parsed}
        )
        
        features = extractor.extract(log)
        print(f"Features: {[f'{f:.3f}' for f in features]}")
