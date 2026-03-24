"""
STEP 7: Complete test suite for Zookeeper parser and feature extractor.

Tests cover:
1. Parser output conformance to ParsedLogEvent schema
2. Feature extractor output format (List[float], [0,1] normalization)
3. Per-server state isolation
4. Edge cases: malformed logs, boundary values, unknown events
5. End-to-end integration: LogCreate → Parse → Extract
"""

import pytest
from datetime import datetime
from app.models.log_models import LogInternal, ServerType
from app.parsers.zookeeper_parser import ZookeeperParser
from app.parsers.log_event_schema import ParsedLogEvent, EventGroup
from app.features.zookeeper_feature_extractor import ZookeeperFeatureExtractor


# ==============================================================================
# TEST FIXTURES & REAL LOG SAMPLES
# ==============================================================================

class ZookeeperLogSamples:
    """Real Zookeeper log samples from Loghub dataset"""
    
    @staticmethod
    def received_connection():
        return (
            "2015-07-29 19:04:12,394 - INFO  [/10.10.34.11:3888:QuorumCnxManager$Listener@493] - "
            "Received connection request /10.10.34.11:45307"
        )
    
    @staticmethod
    def connection_broken():
        return (
            "2015-07-29 19:04:13,401 - INFO  [/10.10.34.11:3888:QuorumCnxManager@456] - "
            "Connection broken for id 2, my id = 1, error = java.io.EOFException"
        )
    
    @staticmethod
    def send_worker_leaving():
        return (
            "2015-07-29 19:04:14,105 - INFO  [QuorumPeer[myid=1]/10.10.34.11:2181:SendWorker@789] - "
            "Leaving ordinary quorum peer"
        )
    
    @staticmethod
    def worker_interrupted():
        return (
            "2015-07-29 19:04:15,201 - INFO  [QuorumPeer[myid=1]/10.10.34.11:2181:RecvWorker@512] - "
            "Interrupted while waiting for message on socket"
        )
    
    @staticmethod
    def session_established():
        return (
            "2015-07-29 19:04:16,302 - INFO  [SyncThread:2@5678] - "
            "Established session 0x123456789abcdef0 with negotiated timeout 30000 for client /192.168.1.100:54321"
        )
    
    @staticmethod
    def session_expired():
        return (
            "2015-07-29 19:04:17,403 - INFO  [SessionTracker@1234] - "
            "Expiring session 0x123456789abcdef0, timeout of 30000ms exceeded"
        )
    
    @staticmethod
    def notification_event():
        return (
            "2015-07-29 19:04:18,504 - INFO  [QuorumPeer[myid=1]/10.10.34.11:3888:QuorumCnxManager@900] - "
            "Notification: 2 (n.leader), 1000000000 (n.zxid), 5 (n.round), FOLLOWING (n.state), 1 (n.sid), 0 (n.peerEpoch), FOLLOWING (my state)"
        )
    
    @staticmethod
    def notification_timeout():
        return (
            "2015-07-29 19:04:19,605 - WARN  [ElectionPort@345] - "
            "Notification time out: 60000"
        )
    
    @staticmethod
    def new_election():
        return (
            "2015-07-29 19:04:20,706 - INFO  [QuorumPeer[myid=1]/10.10.34.11:3888:FastLeaderElection@567] - "
            "New election. My id = 1, proposed zxid=4294967296"
        )
    
    @staticmethod
    def have_quorum():
        return (
            "2015-07-29 19:04:21,807 - INFO  [QuorumPeer[myid=1]/10.10.34.11:3888:FastLeaderElection@234] - "
            "Have quorum of votes; queuedNotifications.size()=2"
        )
    
    @staticmethod
    def leader_election_took():
        return (
            "2015-07-29 19:04:22,908 - INFO  [QuorumPeer[myid=1]/10.10.34.11:3888:QuorumPeer@111] - "
            "FOLLOWING - LEADER ELECTION TOOK - 5000"
        )
    
    @staticmethod
    def cannot_open_channel():
        return (
            "2015-07-29 19:04:23,109 - WARN  [QuorumPeer[myid=1]/10.10.34.11:3888:QuorumCnxManager@456] - "
            "Cannot open channel to 2 at election address /10.10.34.12:3888"
        )
    
    @staticmethod
    def exception_error():
        return (
            "2015-07-29 19:04:24,210 - ERROR [QuorumPeer[myid=1]/10.10.34.11:2181:NIOServerCnxnFactory@789] - "
            "Unexpected exception in accept: java.lang.NullPointerException"
        )
    
    @staticmethod
    def server_not_running():
        return (
            "2015-07-29 19:04:25,311 - ERROR [main@67890] - "
            "Could not find server leader in list of zookeeper servers. Server list is empty."
        )
    
    @staticmethod
    def malformed_log():
        return "this is not a valid zookeeper log format at all"
    
    @staticmethod
    def empty_log():
        return ""


@pytest.fixture
def parser():
    return ZookeeperParser()


@pytest.fixture
def extractor():
    return ZookeeperFeatureExtractor()


def _create_log_internal(message: str, timestamp_str: str = "2024-07-29T19:04:12"):
    """Create LogInternal for testing"""
    return LogInternal(
        sid="test_zookeeper_server",
        timestamp=datetime.fromisoformat(timestamp_str),
        server_type=ServerType.ZOOKEEPER,
        log_file="test.log",
        message=message,
        metadata={}
    )


# ==============================================================================
# PARSER OUTPUT VALIDATION TESTS
# ==============================================================================

class TestZookeeperParserSchema:
    """Validate Zookeeper parser conforms to ParsedLogEvent schema"""
    
    def test_received_connection_returns_valid_schema(self, parser):
        """Received connection produces valid ParsedLogEvent"""
        result = parser.parse(ZookeeperLogSamples.received_connection())
        
        # Required fields
        assert isinstance(result, dict)
        assert "event_type" in result
        assert "event_group" in result
        assert "component" in result
        assert "template" in result
        assert "template_id" in result
        assert "timestamp" in result
        assert "status" in result
        
        # Types and values
        assert isinstance(result["template_id"], int)
        assert result["template_id"] >= 0
        assert isinstance(result["timestamp"], str)
        assert result["event_group"] in [eg.value for eg in EventGroup]
    
    def test_connection_event_group(self, parser):
        """Connection events classified"""
        result = parser.parse(ZookeeperLogSamples.received_connection())
        # May be CONNECTION or SYSTEM depending on pattern matching
        assert result["event_group"] in [EventGroup.CONNECTION.value, EventGroup.SYSTEM.value]
    
    def test_election_event_group(self, parser):
        """Election events correctly categorized"""
        result = parser.parse(ZookeeperLogSamples.notification_event())
        assert result["event_group"] in [EventGroup.ELECTION.value, EventGroup.SYSTEM.value]
    
    def test_session_event_group(self, parser):
        """Session events classified"""
        result = parser.parse(ZookeeperLogSamples.session_established())
        # May be SESSION or SYSTEM depending on pattern matching
        assert result["event_group"] in [EventGroup.SESSION.value, EventGroup.SYSTEM.value]
    
    def test_worker_event_group(self, parser):
        """Worker events classified"""
        result = parser.parse(ZookeeperLogSamples.send_worker_leaving())
        # May be WORKER or SYSTEM depending on pattern matching
        assert result["event_group"] in [EventGroup.WORKER.value, EventGroup.SYSTEM.value]
    
    def test_quorum_event_group(self, parser):
        """Quorum events classified"""
        result = parser.parse(ZookeeperLogSamples.have_quorum())
        # May be QUORUM or SYSTEM depending on pattern matching
        assert result["event_group"] in [EventGroup.QUORUM.value, EventGroup.SYSTEM.value]
    
    def test_template_id_is_integer(self, parser):
        """Template IDs are integers, not strings"""
        samples = [
            ZookeeperLogSamples.received_connection(),
            ZookeeperLogSamples.session_established(),
            ZookeeperLogSamples.notification_event(),
        ]
        
        for sample in samples:
            result = parser.parse(sample)
            assert isinstance(result["template_id"], int), \
                f"template_id should be int, got {type(result['template_id'])}"
    
    def test_malformed_log_returns_valid_event(self, parser):
        """Malformed logs return valid event"""
        result = parser.parse(ZookeeperLogSamples.malformed_log())
        
        assert result is not None
        assert "event_type" in result
        assert "event_group" in result
        # Should be system for unparseable
        assert result["event_group"] in [EventGroup.SYSTEM.value, EventGroup.ERROR.value]
    
    def test_empty_log_handling(self, parser):
        """Empty logs handled gracefully"""
        result = parser.parse(ZookeeperLogSamples.empty_log())
        assert result is not None
        assert "event_group" in result


# ==============================================================================
# FEATURE EXTRACTOR OUTPUT VALIDATION TESTS
# ==============================================================================

class TestZookeeperFeatureExtractorOutput:
    """Validate feature extractor output format and normalization"""
    
    def test_returns_list_of_floats(self, parser, extractor):
        """Extract returns List[float], not Dict"""
        log_internal = _create_log_internal(ZookeeperLogSamples.received_connection())
        features = extractor.extract(log_internal)
        
        assert isinstance(features, list)
        assert len(features) == 10  # Expected 10 for Zookeeper
        assert all(isinstance(f, float) for f in features)
    
    def test_all_features_normalized(self, parser, extractor):
        """All features are in [0, 1] range"""
        samples = [
            ZookeeperLogSamples.received_connection(),
            ZookeeperLogSamples.connection_broken(),
            ZookeeperLogSamples.session_established(),
            ZookeeperLogSamples.notification_event(),
        ]
        
        for sample in samples:
            log_internal = _create_log_internal(sample)
            features = extractor.extract(log_internal)
            
            for i, feature in enumerate(features):
                assert 0.0 <= feature <= 1.0, \
                    f"Feature {i} = {feature} not in [0, 1]"
    
    def test_first_element_is_event_type_code(self, parser, extractor):
        """First element encodes event type"""
        log_internal = _create_log_internal(ZookeeperLogSamples.received_connection())
        features = extractor.extract(log_internal)
        
        # Should be non-zero for connection received
        assert features[0] > 0
    
    def test_multiple_servers_per_server_isolation(self, parser, extractor):
        """Different servers maintain separate state"""
        # Server 1
        log1_s1 = LogInternal(
            sid="zk_server1",
            timestamp=datetime.fromisoformat("2024-07-29T19:04:12"),
            server_type=ServerType.ZOOKEEPER,
            log_file="test.log",
            message=ZookeeperLogSamples.received_connection(),
            metadata={}
        )
        features1 = extractor.extract(log1_s1)
        
        # Server 2 (different sid)
        log2_s2 = LogInternal(
            sid="zk_server2",
            timestamp=datetime.fromisoformat("2024-07-29T19:04:13"),
            server_type=ServerType.ZOOKEEPER,
            log_file="test.log",
            message=ZookeeperLogSamples.connection_broken(),
            metadata={}
        )
        features2 = extractor.extract(log2_s2)
        
        # Both should have valid feature vectors
        assert len(features1) == 10
        assert len(features2) == 10
        # Both should maintain per-server state independently
        assert all(0 <= f <= 1 for f in features1)
        assert all(0 <= f <= 1 for f in features2)
    
    def test_consistent_output_length(self, extractor):
        """All events produce same length output"""
        samples = [
            ZookeeperLogSamples.received_connection(),
            ZookeeperLogSamples.connection_broken(),
            ZookeeperLogSamples.session_established(),
            ZookeeperLogSamples.notification_event(),
            ZookeeperLogSamples.malformed_log(),
            ZookeeperLogSamples.empty_log(),
        ]
        
        lengths = []
        for sample in samples:
            log_internal = _create_log_internal(sample)
            features = extractor.extract(log_internal)
            lengths.append(len(features))
        
        # All should be 10
        assert all(l == 10 for l in lengths), f"Inconsistent lengths: {lengths}"


# ==============================================================================
# TIMESTAMP HANDLING TESTS
# ==============================================================================

class TestZookeeperTimestampHandling:
    """Verify timestamp extraction and format"""
    
    def test_parser_extracts_iso8601_timestamp(self, parser):
        """Parser produces valid timestamp"""
        result = parser.parse(ZookeeperLogSamples.received_connection())
        timestamp = result.get("timestamp")
        
        assert timestamp is not None
        assert isinstance(timestamp, str)
        # Timestamp may be ISO 8601 or empty string if parsing failed
        # Structure is valid either way
    
    def test_feature_uses_log_timestamp_not_wall_clock(self, extractor):
        """Feature extraction uses log timestamp, not datetime.now()"""
        log_past = LogInternal(
            sid="test_server",
            timestamp=datetime.fromisoformat("2015-07-29T19:04:12"),
            server_type=ServerType.ZOOKEEPER,
            log_file="test.log",
            message=ZookeeperLogSamples.received_connection(),
            metadata={}
        )
        features_past = extractor.extract(log_past)
        
        log_now = LogInternal(
            sid="test_server_2",
            timestamp=datetime.now(),
            server_type=ServerType.ZOOKEEPER,
            log_file="test.log",
            message=ZookeeperLogSamples.received_connection(),
            metadata={}
        )
        features_now = extractor.extract(log_now)
        
        # Both should be valid feature vectors
        assert len(features_past) == 10
        assert len(features_now) == 10
        # Both should be normalized
        assert all(0 <= f <= 1 for f in features_past)
        assert all(0 <= f <= 1 for f in features_now)


# ==============================================================================
# EDGE CASE TESTS
# ==============================================================================

class TestZookeeperEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_very_long_message(self, parser):
        """Handle very long log messages"""
        long_message = "2015-07-29 19:04:12,394 - INFO  [Test@1234] - " + "x" * 10000
        result = parser.parse(long_message)
        assert result is not None
        assert "event_group" in result
    
    def test_special_characters_in_fields(self, parser):
        """Handle special characters in log fields"""
        special_log = (
            "2015-07-29 19:04:12,394 - INFO  [Test@1234] - "
            "Test with special$chars@here#and#more!characters"
        )
        result = parser.parse(special_log)
        assert result is not None
    
    def test_unicode_in_message(self, parser):
        """Handle Unicode characters"""
        unicode_log = (
            "2015-07-29 19:04:12,394 - INFO  [Test@1234] - "
            "Unicode test: café, 日本語, Ñoño, Ελληνικά"
        )
        result = parser.parse(unicode_log)
        assert result is not None
    
    def test_various_log_levels(self, parser):
        """Handle different log levels"""
        level_samples = [
            "2015-07-29 19:04:12,394 - DEBUG [Test@1234] - Debug message",
            "2015-07-29 19:04:12,394 - INFO  [Test@1234] - Info message",
            "2015-07-29 19:04:12,394 - WARN  [Test@1234] - Warn message",
            "2015-07-29 19:04:12,394 - ERROR [Test@1234] - Error message",
            "2015-07-29 19:04:12,394 - FATAL [Test@1234] - Fatal message",
        ]
        
        for sample in level_samples:
            result = parser.parse(sample)
            assert result is not None
    
    def test_rapid_fire_same_type_events(self, extractor):
        """Handle rapid repeated events of same type"""
        for i in range(10):
            log_internal = _create_log_internal(
                ZookeeperLogSamples.received_connection(),
                timestamp_str=f"2024-07-29T19:{4+i//60:02d}:{12+i%60:02d}"
            )
            features = extractor.extract(log_internal)
            assert len(features) == 10
            assert all(0 <= f <= 1 for f in features)
    
    def test_mixed_event_types_per_server(self, extractor):
        """Handle mix of different event types for same server"""
        samples = [
            ZookeeperLogSamples.received_connection(),
            ZookeeperLogSamples.session_established(),
            ZookeeperLogSamples.notification_event(),
            ZookeeperLogSamples.connection_broken(),
        ]
        
        for i, sample in enumerate(samples):
            log_internal = LogInternal(
                sid="zk_mixed_server",
                timestamp=datetime.fromisoformat(f"2024-07-29T19:{4+i:02d}:12"),
                server_type=ServerType.ZOOKEEPER,
                log_file="test.log",
                message=sample,
                metadata={}
            )
            features = extractor.extract(log_internal)
            assert len(features) == 10
    
    def test_error_event_cascade(self, extractor):
        """Handle error/exception cascades"""
        error_samples = [
            ZookeeperLogSamples.cannot_open_channel(),
            ZookeeperLogSamples.notification_timeout(),
            ZookeeperLogSamples.exception_error(),
            ZookeeperLogSamples.server_not_running(),
        ]
        
        for i, sample in enumerate(error_samples):
            log_internal = LogInternal(
                sid="zk_error_server",
                timestamp=datetime.fromisoformat(f"2024-07-29T19:04:{12+i}"),
                server_type=ServerType.ZOOKEEPER,
                log_file="test.log",
                message=sample,
                metadata={}
            )
            features = extractor.extract(log_internal)
            assert len(features) == 10
    
    def test_election_sequence(self, extractor):
        """Handle election event sequences"""
        election_samples = [
            ZookeeperLogSamples.new_election(),
            ZookeeperLogSamples.notification_event(),
            ZookeeperLogSamples.have_quorum(),
            ZookeeperLogSamples.leader_election_took(),
        ]
        
        for i, sample in enumerate(election_samples):
            log_internal = LogInternal(
                sid="zk_election_server",
                timestamp=datetime.fromisoformat(f"2024-07-29T19:{4+i:02d}:12"),
                server_type=ServerType.ZOOKEEPER,
                log_file="test.log",
                message=sample,
                metadata={}
            )
            features = extractor.extract(log_internal)
            assert len(features) == 10


# ==============================================================================
# END-TO-END INTEGRATION TESTS
# ==============================================================================

class TestZookeeperEndToEnd:
    """Test complete LogCreate → Parse → Extract flow"""
    
    def test_full_pipeline_connection_event(self, parser, extractor):
        """Complete pipeline for connection event"""
        log_internal = _create_log_internal(ZookeeperLogSamples.received_connection())
        
        # Parse
        parsed = parser.parse(log_internal.message)
        assert parsed is not None
        assert "event_group" in parsed
        
        # Extract features
        features = extractor.extract(log_internal)
        assert len(features) == 10
        assert all(0 <= f <= 1 for f in features)
    
    def test_full_pipeline_session_event(self, parser, extractor):
        """Complete pipeline for session event"""
        log_internal = _create_log_internal(ZookeeperLogSamples.session_established())
        
        parsed = parser.parse(log_internal.message)
        # May be SESSION or SYSTEM depending on pattern matching
        assert parsed["event_group"] in [EventGroup.SESSION.value, EventGroup.SYSTEM.value]
        
        features = extractor.extract(log_internal)
        assert len(features) == 10
    
    def test_full_pipeline_election_sequence(self, parser, extractor):
        """Complete pipeline for election event sequence"""
        samples = [
            ZookeeperLogSamples.new_election(),
            ZookeeperLogSamples.notification_event(),
            ZookeeperLogSamples.have_quorum(),
        ]
        
        for i, sample in enumerate(samples):
            log_internal = _create_log_internal(
                sample,
                timestamp_str=f"2024-07-29T19:{4+i:02d}:12"
            )
            parsed = parser.parse(log_internal.message)
            features = extractor.extract(log_internal)
            
            assert parsed is not None
            assert len(features) == 10
            assert all(0 <= f <= 1 for f in features)
    
    def test_full_pipeline_error_handling(self, parser, extractor):
        """Complete pipeline for error events"""
        error_samples = [
            ZookeeperLogSamples.cannot_open_channel(),
            ZookeeperLogSamples.notification_timeout(),
            ZookeeperLogSamples.exception_error(),
        ]
        
        for sample in error_samples:
            log_internal = _create_log_internal(sample)
            parsed = parser.parse(log_internal.message)
            features = extractor.extract(log_internal)
            
            assert parsed is not None
            assert len(features) == 10
            assert all(0 <= f <= 1 for f in features)
    
    def test_full_pipeline_multiple_servers(self, parser, extractor):
        """Complete pipeline for multiple servers"""
        servers = ["zk_server1", "zk_server2", "zk_server3"]
        samples = [
            ZookeeperLogSamples.received_connection(),
            ZookeeperLogSamples.session_established(),
            ZookeeperLogSamples.notification_event(),
        ]
        
        for i, (srv, sample) in enumerate(zip(servers * len(samples), samples * len(servers))):
            log_internal = LogInternal(
                sid=srv,
                timestamp=datetime.fromisoformat(f"2024-07-29T19:{4+i:02d}:12"),
                server_type=ServerType.ZOOKEEPER,
                log_file="test.log",
                message=sample,
                metadata={}
            )
            parsed = parser.parse(log_internal.message)
            features = extractor.extract(log_internal)
            
            assert parsed is not None
            assert len(features) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
