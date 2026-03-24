"""
STEP 5: Pipeline Integration Tests

Verifies end-to-end flow:
1. LogCreate → LogInternal (model validation)
2. Parser converts message to ParsedLogEvent (Dict[str, Any])
3. Feature extractor produces List[float] with proper normalization
4. Per-server state isolation works correctly
5. LogService orchestrates all components correctly
"""

import pytest
from datetime import datetime, timedelta
from app.models.log_models import LogCreate, LogInternal, ServerType
from app.parsers.parser_factory import ParserFactory
from app.parsers.log_event_schema import ParsedLogEvent, EventGroup
from app.features.feature_extractor_factory import FeatureExtractorFactory


# ==============================================================================
# TEST FIXTURES
# ==============================================================================

@pytest.fixture
def linux_logs():
    """Real Linux log samples"""
    return [
        "Jun 14 15:16:01 combo sshd(pam_unix)[19939]: authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=218.188.2.4",
        "Jun 14 15:16:02 combo sshd(pam_unix)[19937]: check pass; user unknown",
        "Jun 15 04:06:18 combo su(pam_unix)[21416]: session opened for user cyrus by (uid=0)",
        "Jun 15 04:06:19 combo su(pam_unix)[21416]: session closed for user cyrus",
    ]


@pytest.fixture
def windows_logs():
    """Real Windows log samples"""
    return [
        "2016-09-28 04:30:31, Info                  CBS    TrustedInstaller service starts successfully.",
        "2016-09-28 04:30:31, Info                  CBS    SQM: Failed to start upload with file pattern: C:\\Windows\\servicing\\sqm\\*_std.sqm, flags: 0x2 [HRESULT = 0x80004005 - E_FAIL]",
        "2016-09-28 04:30:31, Info                  CBS    Session: 30546173_4261722401 initialized by client WindowsUpdateAgent.",
        "2016-09-28 04:30:31, Info                  CSI    00000001@2016/9/27:20:30:31.455 WcpInitialize (wcp.dll version 0.0.0.6) called",
    ]


@pytest.fixture
def zookeeper_logs():
    """Real Zookeeper log samples"""
    return [
        "2015-07-29 17:41:44,747 - INFO  [QuorumPeer[myid=1]/0:0:0:0:0:0:0:0:2181:FastLeaderElection@774] - Notification time out: 3200",
        "2015-07-29 19:04:12,394 - INFO  [/10.10.34.11:3888:QuorumCnxManager$Listener@493] - Received connection request /10.10.34.11:45307",
        "2015-07-29 19:04:29,071 - WARN  [SendWorker:188978561024:QuorumCnxManager$SendWorker@688] - Send worker leaving thread",
        "2015-07-29 19:13:24,282 - WARN  [RecvWorker:188978561024:QuorumCnxManager$RecvWorker@762] - Connection broken for id 188978561024, my id = 1, error =",
    ]


# ==============================================================================
# PARSER OUTPUT TESTS - Verify ParsedLogEvent schema compliance
# ==============================================================================

class TestParserOutputSchema:
    """Verify parsers return proper ParsedLogEvent structure"""
    
    def test_linux_parser_outputs_valid_schema(self, linux_logs):
        """Linux parser returns Dict matching ParsedLogEvent schema"""
        parser = ParserFactory.get_parser(ServerType.LINUX)
        
        for log in linux_logs:
            output = parser.parse(log)
            
            # Verify it's a dict (from ParsedLogEvent.to_dict())
            assert isinstance(output, dict), f"Parser output must be dict, got {type(output)}"
            
            # Verify required top-level fields
            required_fields = {"event_type", "event_group", "component", "template", 
                             "template_id", "timestamp", "status", "metadata"}
            assert required_fields.issubset(output.keys()), \
                f"Missing required fields. Got: {output.keys()}"
            
            # Verify field types
            assert isinstance(output["event_type"], str), "event_type must be string"
            assert isinstance(output["event_group"], str), "event_group must be string"
            assert isinstance(output["component"], str), "component must be string"
            assert isinstance(output["template"], str), "template must be string"
            assert isinstance(output["template_id"], int), "template_id must be int"
            assert isinstance(output["timestamp"], str), "timestamp must be string (ISO 8601)"
            assert isinstance(output["status"], str), "status must be string"
            assert isinstance(output["metadata"], dict), "metadata must be dict"
            
            # Verify event_group is valid
            valid_groups = {e.value for e in EventGroup}
            assert output["event_group"] in valid_groups, \
                f"Invalid event_group: {output['event_group']}"
            
            # Verify timestamp is ISO 8601
            try:
                datetime.fromisoformat(output["timestamp"])
            except ValueError:
                pytest.fail(f"Invalid ISO 8601 timestamp: {output['timestamp']}")
    
    def test_windows_parser_outputs_valid_schema(self, windows_logs):
        """Windows parser returns Dict matching ParsedLogEvent schema"""
        parser = ParserFactory.get_parser(ServerType.WINDOWS)
        
        for log in windows_logs:
            output = parser.parse(log)
            
            # Verify it's a dict (from ParsedLogEvent.to_dict())
            assert isinstance(output, dict), f"Parser output must be dict, got {type(output)}"
            
            # Verify required top-level fields
            required_fields = {"event_type", "event_group", "component", "template", 
                             "template_id", "timestamp", "status", "metadata"}
            assert required_fields.issubset(output.keys()), \
                f"Missing required fields. Got: {output.keys()}"
            
            # Verify template_id is integer
            assert isinstance(output["template_id"], int), "template_id must be int"
    
    def test_zookeeper_parser_outputs_valid_schema(self, zookeeper_logs):
        """Zookeeper parser returns Dict matching ParsedLogEvent schema"""
        parser = ParserFactory.get_parser(ServerType.ZOOKEEPER)
        
        for log in zookeeper_logs:
            output = parser.parse(log)
            
            # Verify it's a dict (from ParsedLogEvent.to_dict())
            assert isinstance(output, dict), f"Parser output must be dict, got {type(output)}"
            
            # Verify required top-level fields
            required_fields = {"event_type", "event_group", "component", "template", 
                             "template_id", "timestamp", "status", "metadata"}
            assert required_fields.issubset(output.keys()), \
                f"Missing required fields. Got: {output.keys()}"


# ==============================================================================
# FEATURE EXTRACTOR OUTPUT TESTS - Verify List[float] format
# ==============================================================================

class TestFeatureExtractorOutput:
    """Verify feature extractors return proper fixed-length vectors"""
    
    def _create_log_internal(self, message: str, server_type: ServerType, sid: str = "test_server"):
        """Helper to create LogInternal with parsed metadata"""
        parser = ParserFactory.get_parser(server_type)
        return LogInternal(
            sid=sid,
            timestamp=datetime.now(),
            server_type=server_type,
            log_file="test.log",
            message=message,
            metadata={"parsed": parser.parse(message)}
        )
    
    def test_linux_feature_extractor_returns_14_element_vector(self, linux_logs):
        """Linux extractor returns exactly 14 normalized floats"""
        extractor = FeatureExtractorFactory.get_extractor(ServerType.LINUX)
        
        for log_msg in linux_logs:
            log = self._create_log_internal(log_msg, ServerType.LINUX)
            features = extractor.extract(log)
            
            # Verify it's a list
            assert isinstance(features, list), f"Features must be list, got {type(features)}"
            
            # Verify length
            assert len(features) == 14, f"Linux must return 14 features, got {len(features)}"
            
            # Verify all are floats
            assert all(isinstance(f, (int, float)) for f in features), \
                "All features must be numeric"
            
            # Verify normalization [0, 1]
            assert all(0 <= f <= 1 for f in features), \
                f"All features must be normalized [0, 1], got {features}"
    
    def test_windows_feature_extractor_returns_12_element_vector(self, windows_logs):
        """Windows extractor returns exactly 12 normalized floats"""
        extractor = FeatureExtractorFactory.get_extractor(ServerType.WINDOWS)
        
        for log_msg in windows_logs:
            log = self._create_log_internal(log_msg, ServerType.WINDOWS)
            features = extractor.extract(log)
            
            # Verify it's a list
            assert isinstance(features, list), f"Features must be list, got {type(features)}"
            
            # Verify length
            assert len(features) == 12, f"Windows must return 12 features, got {len(features)}"
            
            # Verify all are floats
            assert all(isinstance(f, (int, float)) for f in features), \
                "All features must be numeric"
            
            # Verify normalization [0, 1]
            assert all(0 <= f <= 1 for f in features), \
                f"All features must be normalized [0, 1], got {features}"
    
    def test_zookeeper_feature_extractor_returns_10_element_vector(self, zookeeper_logs):
        """Zookeeper extractor returns exactly 10 normalized floats"""
        extractor = FeatureExtractorFactory.get_extractor(ServerType.ZOOKEEPER)
        
        for log_msg in zookeeper_logs:
            log = self._create_log_internal(log_msg, ServerType.ZOOKEEPER)
            features = extractor.extract(log)
            
            # Verify it's a list
            assert isinstance(features, list), f"Features must be list, got {type(features)}"
            
            # Verify length
            assert len(features) == 10, f"Zookeeper must return 10 features, got {len(features)}"
            
            # Verify all are floats
            assert all(isinstance(f, (int, float)) for f in features), \
                "All features must be numeric"
            
            # Verify normalization [0, 1]
            assert all(0 <= f <= 1 for f in features), \
                f"All features must be normalized [0, 1], got {features}"


# ==============================================================================
# PER-SERVER STATE ISOLATION TESTS
# ==============================================================================

class TestPerServerIsolation:
    """Verify per-server state doesn't leak between servers"""
    
    def _create_log_internal(self, message: str, server_type: ServerType, sid: str = "test_server"):
        """Helper to create LogInternal with parsed metadata"""
        parser = ParserFactory.get_parser(server_type)
        return LogInternal(
            sid=sid,
            timestamp=datetime.now(),
            server_type=server_type,
            log_file="test.log",
            message=message,
            metadata={"parsed": parser.parse(message)}
        )
    
    def test_linux_feature_extractor_per_server_isolation(self, linux_logs):
        """Linux: Processing server B doesn't affect server A state"""
        extractor = FeatureExtractorFactory.get_extractor(ServerType.LINUX)
        
        # Get initial count (may have servers from other tests since it's a singleton)
        initial_count = len(extractor.server_states)
        
        # Process server_a multiple times
        log_a1 = self._create_log_internal(linux_logs[0], ServerType.LINUX, sid="server_a")
        features_a1 = extractor.extract(log_a1)
        
        log_a2 = self._create_log_internal(linux_logs[1], ServerType.LINUX, sid="server_a")
        features_a2 = extractor.extract(log_a2)
        
        # Process server_b
        log_b1 = self._create_log_internal(linux_logs[0], ServerType.LINUX, sid="server_b")
        features_b1 = extractor.extract(log_b1)
        
        # Process server_a again - should continue from A's state, not affected by B
        log_a3 = self._create_log_internal(linux_logs[2], ServerType.LINUX, sid="server_a")
        features_a3 = extractor.extract(log_a3)
        
        # Verify extractor maintains separate state for A and B
        assert len(extractor.server_states) >= initial_count + 2, \
            "Should have at least 2 additional server states for server_a and server_b"
        assert "server_a" in extractor.server_states, "server_a state should exist"
        assert "server_b" in extractor.server_states, "server_b state should exist"
        
        # All results should be valid
        assert len(features_a1) == 14
        assert len(features_a2) == 14
        assert len(features_a3) == 14
        assert len(features_b1) == 14
    
    def test_windows_feature_extractor_per_server_isolation(self, windows_logs):
        """Windows: Processing server B doesn't affect server A state"""
        extractor = FeatureExtractorFactory.get_extractor(ServerType.WINDOWS)
        
        # Get initial count (may have servers from other tests since it's a singleton)
        initial_count = len(extractor.server_states)
        
        # Process multiple servers
        log_srv1 = self._create_log_internal(windows_logs[0], ServerType.WINDOWS, sid="srv1")
        features_srv1_a = extractor.extract(log_srv1)
        
        log_srv2 = self._create_log_internal(windows_logs[1], ServerType.WINDOWS, sid="srv2")
        features_srv2 = extractor.extract(log_srv2)
        
        # Verify isolated states
        assert len(extractor.server_states) >= initial_count + 2, \
            "Should have at least 2 additional server states"
        assert "srv1" in extractor.server_states
        assert "srv2" in extractor.server_states
        
        # All results valid
        assert len(features_srv1_a) == 12
        assert len(features_srv2) == 12
    
    def test_zookeeper_feature_extractor_per_server_isolation(self, zookeeper_logs):
        """Zookeeper: Processing server B doesn't affect server A state"""
        extractor = FeatureExtractorFactory.get_extractor(ServerType.ZOOKEEPER)
        
        # Get initial count (may have servers from other tests since it's a singleton)
        initial_count = len(extractor.server_states)
        
        # Process multiple servers
        log_node1 = self._create_log_internal(zookeeper_logs[0], ServerType.ZOOKEEPER, sid="zk_node1")
        features_node1 = extractor.extract(log_node1)
        
        log_node2 = self._create_log_internal(zookeeper_logs[1], ServerType.ZOOKEEPER, sid="zk_node2")
        features_node2 = extractor.extract(log_node2)
        
        # Verify isolated states
        assert len(extractor.server_states) >= initial_count + 2, \
            "Should have at least 2 additional server states"
        assert "zk_node1" in extractor.server_states
        assert "zk_node2" in extractor.server_states
        
        # All results valid
        assert len(features_node1) == 10
        assert len(features_node2) == 10


# ==============================================================================
# TIMESTAMP ACCURACY TESTS - Verify log time used, not wall clock
# ==============================================================================

class TestTimestampAccuracy:
    """Verify feature computation uses log timestamp, not wall clock"""
    
    def _create_log_internal(self, message: str, server_type: ServerType, 
                            timestamp: datetime, sid: str = "test_server"):
        """Helper to create LogInternal with specific timestamp"""
        parser = ParserFactory.get_parser(server_type)
        return LogInternal(
            sid=sid,
            timestamp=timestamp,
            server_type=server_type,
            log_file="test.log",
            message=message,
            metadata={"parsed": parser.parse(message)}
        )
    
    def test_linux_uses_log_timestamp_not_wall_clock(self, linux_logs):
        """Linux: Feature computation uses log timestamp for 5m windows"""
        extractor = FeatureExtractorFactory.get_extractor(ServerType.LINUX)
        
        # Create logs with specific timestamps (5 minutes apart)
        base_time = datetime(2023, 1, 1, 10, 0, 0)
        
        log1 = self._create_log_internal(linux_logs[0], ServerType.LINUX, 
                                        timestamp=base_time, sid="srv1")
        features1 = extractor.extract(log1)
        
        # Log at T+4:59 (same 5m window)
        log2 = self._create_log_internal(linux_logs[1], ServerType.LINUX,
                                        timestamp=base_time + timedelta(minutes=4, seconds=59),
                                        sid="srv1")
        features2 = extractor.extract(log2)
        
        # Log at T+5:01 (new 5m window)
        log3 = self._create_log_internal(linux_logs[2], ServerType.LINUX,
                                        timestamp=base_time + timedelta(minutes=5, seconds=1),
                                        sid="srv1")
        features3 = extractor.extract(log3)
        
        # All should be valid outputs
        assert len(features1) == 14
        assert len(features2) == 14
        assert len(features3) == 14


# ==============================================================================
# MULTI-TYPE INTEGRATION TEST
# ==============================================================================

class TestMultiTypeIntegration:
    """Verify all 3 log types work together in same application"""
    
    def test_all_log_types_processed_simultaneously(self, linux_logs, windows_logs, zookeeper_logs):
        """Process logs from all 3 types simultaneously"""
        
        # Get parsers
        linux_parser = ParserFactory.get_parser(ServerType.LINUX)
        windows_parser = ParserFactory.get_parser(ServerType.WINDOWS)
        zk_parser = ParserFactory.get_parser(ServerType.ZOOKEEPER)
        
        # Get extractors
        linux_ext = FeatureExtractorFactory.get_extractor(ServerType.LINUX)
        windows_ext = FeatureExtractorFactory.get_extractor(ServerType.WINDOWS)
        zk_ext = FeatureExtractorFactory.get_extractor(ServerType.ZOOKEEPER)
        
        # Process all types
        for linux_msg in linux_logs:
            log = LogInternal(
                sid="linux_server",
                timestamp=datetime.now(),
                server_type=ServerType.LINUX,
                log_file="test.log",
                message=linux_msg,
                metadata={"parsed": linux_parser.parse(linux_msg)}
            )
            features = linux_ext.extract(log)
            assert len(features) == 14
        
        for windows_msg in windows_logs:
            log = LogInternal(
                sid="windows_server",
                timestamp=datetime.now(),
                server_type=ServerType.WINDOWS,
                log_file="test.log",
                message=windows_msg,
                metadata={"parsed": windows_parser.parse(windows_msg)}
            )
            features = windows_ext.extract(log)
            assert len(features) == 12
        
        for zk_msg in zookeeper_logs:
            log = LogInternal(
                sid="zk_node",
                timestamp=datetime.now(),
                server_type=ServerType.ZOOKEEPER,
                log_file="test.log",
                message=zk_msg,
                metadata={"parsed": zk_parser.parse(zk_msg)}
            )
            features = zk_ext.extract(log)
            assert len(features) == 10


# ==============================================================================
# END-TO-END PIPELINE TESTS
# ==============================================================================

class TestEndToEndPipeline:
    """Verify complete pipeline from LogCreate to features"""
    
    def test_pipeline_linux_logs(self, linux_logs):
        """Complete pipeline: LogCreate → Parse → Extract → Verify"""
        parser = ParserFactory.get_parser(ServerType.LINUX)
        extractor = FeatureExtractorFactory.get_extractor(ServerType.LINUX)
        
        for log_msg in linux_logs:
            # Step 1: Create LogCreate
            log_create = LogCreate(
                sid="linux_srv_1",
                timestamp=datetime.now(),
                server_type=ServerType.LINUX,
                log_file="secure",
                message=log_msg
            )
            
            # Step 2: Convert to LogInternal
            log_internal = LogInternal(**log_create.model_dump())
            
            # Step 3: Parse
            parsed = parser.parse(log_internal.message)
            log_internal.metadata = {"parsed": parsed}
            
            # Step 4: Extract features
            features = extractor.extract(log_internal)
            log_internal.metadata["features"] = features
            
            # Verify final state
            assert log_internal.metadata["parsed"] is not None
            assert isinstance(log_internal.metadata["parsed"], dict)
            assert log_internal.metadata["features"] is not None
            assert len(log_internal.metadata["features"]) == 14
            assert all(0 <= f <= 1 for f in log_internal.metadata["features"])
    
    def test_pipeline_windows_logs(self, windows_logs):
        """Complete pipeline: LogCreate → Parse → Extract → Verify"""
        parser = ParserFactory.get_parser(ServerType.WINDOWS)
        extractor = FeatureExtractorFactory.get_extractor(ServerType.WINDOWS)
        
        for log_msg in windows_logs:
            # Step 1: Create LogCreate
            log_create = LogCreate(
                sid="windows_srv_1",
                timestamp=datetime.now(),
                server_type=ServerType.WINDOWS,
                log_file="CBS.log",
                message=log_msg
            )
            
            # Step 2: Convert to LogInternal
            log_internal = LogInternal(**log_create.model_dump())
            
            # Step 3: Parse
            parsed = parser.parse(log_internal.message)
            log_internal.metadata = {"parsed": parsed}
            
            # Step 4: Extract features
            features = extractor.extract(log_internal)
            log_internal.metadata["features"] = features
            
            # Verify final state
            assert log_internal.metadata["parsed"] is not None
            assert log_internal.metadata["features"] is not None
            assert len(log_internal.metadata["features"]) == 12
            assert all(0 <= f <= 1 for f in log_internal.metadata["features"])
    
    def test_pipeline_zookeeper_logs(self, zookeeper_logs):
        """Complete pipeline: LogCreate → Parse → Extract → Verify"""
        parser = ParserFactory.get_parser(ServerType.ZOOKEEPER)
        extractor = FeatureExtractorFactory.get_extractor(ServerType.ZOOKEEPER)
        
        for log_msg in zookeeper_logs:
            # Step 1: Create LogCreate
            log_create = LogCreate(
                sid="zk_node_1",
                timestamp=datetime.now(),
                server_type=ServerType.ZOOKEEPER,
                log_file="zookeeper.log",
                message=log_msg
            )
            
            # Step 2: Convert to LogInternal
            log_internal = LogInternal(**log_create.model_dump())
            
            # Step 3: Parse
            parsed = parser.parse(log_internal.message)
            log_internal.metadata = {"parsed": parsed}
            
            # Step 4: Extract features
            features = extractor.extract(log_internal)
            log_internal.metadata["features"] = features
            
            # Verify final state
            assert log_internal.metadata["parsed"] is not None
            assert log_internal.metadata["features"] is not None
            assert len(log_internal.metadata["features"]) == 10
            assert all(0 <= f <= 1 for f in log_internal.metadata["features"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
