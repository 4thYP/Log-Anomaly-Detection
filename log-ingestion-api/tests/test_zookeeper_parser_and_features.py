"""
Test suite for Zookeeper log parser and feature extractor.
Tests cover all major event categories and anomaly detection patterns.
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from app.models.log_models import LogInternal, ServerType
from app.parsers.zookeeper_parser import ZookeeperParser, ParsedZookeeperLogEvent
from app.features.zookeeper_feature_extractor import (
    ZookeeperFeatureExtractor,
    get_zookeeper_feature_extractor,
)


# ============================================================================
# TEST DATA - Real Zookeeper logs from Loghub dataset
# ============================================================================

class ZookeeperLogSamples:
    """Collection of real Zookeeper event log samples"""

    @staticmethod
    def notification_timeout() -> str:
        """E31: Notification time out"""
        return "2015-07-29 17:41:44,747 - INFO  [QuorumPeer[myid=1]/0:0:0:0:0:0:0:2181:FastLeaderElection@774] - Notification time out: 3200"

    @staticmethod
    def received_connection_request() -> str:
        """E40: Received connection request"""
        return "2015-07-29 19:04:12,394 - INFO  [/10.10.34.11:3888:QuorumCnxManager$Listener@493] - Received connection request /10.10.34.11:45307"

    @staticmethod
    def send_worker_leaving() -> str:
        """E42: Send worker leaving thread"""
        return "2015-07-29 19:04:29,071 - WARN  [SendWorker:188978561024:QuorumCnxManager$SendWorker@688] - Send worker leaving thread"
    @staticmethod
    def interrupted_waiting() -> str:
        """E24: Interrupted while waiting for message on queue"""
        return "2015-07-29 19:04:29,079 - WARN  [SendWorker:188978561024:QuorumCnxManager$SendWorker@679] - Interrupted while waiting for message on queue"

    @staticmethod
    def connection_broken() -> str:
        """E11: Connection broken for id"""
        return "2015-07-29 19:13:24,282 - WARN  [RecvWorker:188978561024:QuorumCnxManager$RecvWorker@762] - Connection broken for id 188978561024, my id = 1, error ="

    @staticmethod
    def interrupting_sendworker() -> str:
        """E25: Interrupting SendWorker"""
        return "2015-07-29 19:14:07,559 - WARN  [RecvWorker:188978561024:QuorumCnxManager$RecvWorker@765] - Interrupting SendWorker"

    @staticmethod
    def connection_broken_cascade_1() -> str:
        """E11: First break in cascade"""
        return "2015-07-29 19:13:27,721 - WARN  [RecvWorker:188978561024:QuorumCnxManager$RecvWorker@762] - Connection broken for id 188978561024, my id = 1, error ="

    @staticmethod
    def connection_broken_cascade_2() -> str:
        """E11: Second break in cascade"""
        return "2015-07-29 19:13:34,382 - WARN  [RecvWorker:188978561024:QuorumCnxManager$RecvWorker@762] - Connection broken for id 188978561024, my id = 1, error ="

    @staticmethod
    def connection_broken_cascade_3() -> str:
        """E11: Third break in cascade"""
        return "2015-07-29 19:13:47,731 - WARN  [RecvWorker:188978561024:QuorumCnxManager$RecvWorker@762] - Connection broken for id 188978561024, my id = 1, error ="

    @staticmethod
    def connection_broken_cascade_4() -> str:
        """E11: Fourth break in cascade"""
        return "2015-07-29 19:13:54,399 - WARN  [RecvWorker:188978561024:QuorumCnxManager$RecvWorker@762] - Connection broken for id 188978561024, my id = 1, error ="

    @staticmethod
    def connection_broken_cascade_5() -> str:
        """E11: Fifth break (triggers anomaly)"""
        return "2015-07-29 19:16:24,348 - WARN  [RecvWorker:188978561024:QuorumCnxManager$RecvWorker@762] - Connection broken for id 188978561024, my id = 1, error ="

    @staticmethod
    def established_session() -> str:
        """E13: Established session with negotiated timeout"""
        return "2015-07-30 10:20:45,123 - INFO  [NIOServerCnxn.Factory:0:NIOServerCnxn@456] - Established session 0x15678934abcdef0 with negotiated timeout 30000 for client /10.10.34.11:50432"

    @staticmethod
    def session_expired() -> str:
        """E15: Expiring session, timeout exceeded"""
        return "2015-07-30 10:21:15,456 - INFO  [SessionTracker:0:SessionTracker@789] - Expiring session 0x15678934abcdef0, timeout of 30000ms exceeded"

    @staticmethod
    def client_new_session() -> str:
        """E7: Client attempting to establish new session"""
        return "2015-07-30 10:20:30,000 - INFO  [NIOServerCnxn.Factory:0:NIOServerCnxn@432] - Client attempting to establish new session at /10.10.34.12:50123"

    @staticmethod
    def client_renew_session() -> str:
        """E8: Client attempting to renew session"""
        return "2015-07-30 10:21:00,000 - INFO  [NIOServerCnxn.Factory:0:NIOServerCnxn@450] - Client attempting to renew session 0x15678934abcdef0 at /10.10.34.12:50123"

    @staticmethod
    def notification_event() -> str:
        """E32-E37: Election notification"""
        return "2015-07-30 11:00:00,000 - INFO  [QuorumPeer[myid=1]/0:0:0:0:0:0:0:2181:FastLeaderElection@555] - Notification: 1 (n.leader), 0 (n.zxid), 1 (n.round), LOOKING (n.state), 2 (n.sid), 0 (n.peerEpoch), FOLLOWING (my state)"

    @staticmethod
    def new_election() -> str:
        """E30: New election"""
        return "2015-07-30 11:00:05,000 - INFO  [QuorumPeer[myid=1]/0:0:0:0:0:0:0:2181:FastLeaderElection@560] - New election. My id =  1, proposed zxid=100"

    @staticmethod
    def have_quorum() -> str:
        """E22: Have quorum of supporters"""
        return "2015-07-30 11:00:10,000 - INFO  [QuorumPeer[myid=1]/0:0:0:0:0:0:0:2181:QuorumPeer@700] - Have quorum of supporters; starting up and setting last processed zxid: 100"

    @staticmethod
    def following_state() -> str:
        """E18: FOLLOWING state"""
        return "2015-07-30 11:00:12,000 - INFO  [QuorumPeer[myid=1]/0:0:0:0:0:0:0:2181:QuorumPeer@710] - FOLLOWING"

    @staticmethod
    def leader_election_took() -> str:
        """E19: Leader election took time"""
        return "2015-07-30 11:00:15,000 - INFO  [QuorumPeer[myid=1]/0:0:0:0:0:0:0:2181:QuorumPeer@720] - FOLLOWING - LEADER ELECTION TOOK - 15000"

    @staticmethod
    def getting_snapshot() -> str:
        """E20: Getting snapshot from leader"""
        return "2015-07-30 11:00:20,000 - INFO  [QuorumPeer[myid=1]/0:0:0:0:0:0:0:2181:Follower@800] - Getting a snapshot from leader"

    @staticmethod
    def cannot_open_channel() -> str:
        """E5: Cannot open channel to peer"""
        return "2015-07-30 11:05:00,000 - WARN  [QuorumPeer[myid=1]/0:0:0:0:0:0:0:2181:QuorumCnxManager@600] - Cannot open channel to 2 at election address /10.10.34.13:3888"

    @staticmethod
    def end_of_stream() -> str:
        """E6: Caught end of stream exception"""
        return "2015-07-30 11:05:30,000 - WARN  [NIOServerCnxn.Factory:0:NIOServerCnxn@500] - caught end of stream exception"

    @staticmethod
    def unexpected_exception() -> str:
        """E50: Unexpected Exception"""
        return "2015-07-30 12:00:00,000 - ERROR [QuorumPeer[myid=1]/0:0:0:0:0:0:0:2181:QuorumPeer@999] - Unexpected Exception:"

    @staticmethod
    def server_not_running() -> str:
        """E14: ZooKeeperServer not running"""
        return "2015-07-30 12:30:00,000 - ERROR [NIOServerCnxn.Factory:0:NIOServerCnxn@888] - Exception causing close of session 0x15678934abcdef0 due to java.io.IOException: ZooKeeperServer not running"

    @staticmethod
    def closed_socket_with_session() -> str:
        """E10: Closed socket connection (with session)"""
        return "2015-07-30 10:21:30,000 - INFO  [NIOServerCnxn.Factory:0:NIOServerCnxn@880] - Closed socket connection for client /10.10.34.11:50432 which had sessionid 0x15678934abcdef0"

    @staticmethod
    def closed_socket_no_session() -> str:
        """E9: Closed socket connection (no session)"""
        return "2015-07-30 10:19:00,000 - INFO  [NIOServerCnxn.Factory:0:NIOServerCnxn@870] - Closed socket connection for client /10.10.34.14:60123 (no session established for client)"

    @staticmethod
    def accepted_socket() -> str:
        """E2: Accepted socket connection"""
        return "2015-07-30 10:15:00,000 - INFO  [NIOServerCnxn.Factory:0:NIOServerCnxn@400] - Accepted socket connection from /10.10.34.15:45678"

    @staticmethod
    def unknown_format() -> str:
        """Unparseable format (error handling)"""
        return "This is not a valid Zookeeper log format."


# ============================================================================
# PARSER TESTS
# ============================================================================

class TestZookeeperParser:
    """Test suite for Zookeeper log parser"""

    @pytest.fixture
    def parser(self) -> ZookeeperParser:
        """Create parser instance"""
        return ZookeeperParser()

    def test_notification_timeout_parsing(self, parser: ZookeeperParser):
        """Test notification timeout event"""
        log_line = ZookeeperLogSamples.notification_timeout()
        result = parser.parse(log_line)

        assert result["event_type"] == "election_notification_timeout"
        assert result["template_id"] == "E31"
        assert result["notification_timeout"] == 3200
        assert result["status"] == "info"
        assert result["parsed_successfully"] is True

    def test_received_connection_parsing(self, parser: ZookeeperParser):
        """Test received connection event"""
        log_line = ZookeeperLogSamples.received_connection_request()
        result = parser.parse(log_line)

        assert result["event_type"] == "connection_received"
        assert result["template_id"] == "E40"
        assert result["remote_ip"] == "10.10.34.11"
        assert result["remote_port"] == 45307
        assert result["local_port"] == 3888

    def test_send_worker_leaving_parsing(self, parser: ZookeeperParser):
        """Test send worker leaving event"""
        log_line = ZookeeperLogSamples.send_worker_leaving()
        result = parser.parse(log_line)

        assert result["event_type"] == "worker_send_leaving"
        assert result["template_id"] == "E42"
        assert result["worker_type"] == "SendWorker"
        assert result["status"] == "warning"

    def test_interrupted_waiting_parsing(self, parser: ZookeeperParser):
        """Test interrupted waiting event"""
        log_line = ZookeeperLogSamples.interrupted_waiting()
        result = parser.parse(log_line)

        assert result["event_type"] == "worker_interrupted"
        assert result["template_id"] == "E24"
        assert result["status"] == "warning"

    def test_connection_broken_parsing(self, parser: ZookeeperParser):
        """Test connection broken event"""
        log_line = ZookeeperLogSamples.connection_broken()
        result = parser.parse(log_line)

        assert result["event_type"] == "connection_broken"
        assert result["template_id"] == "E11"
        assert result["peer_id"] == 188978561024
        assert result["my_id"] == 1
        assert result["status"] == "failure"
        assert result["error_reason"] == "Connection broken"

    def test_interrupting_sendworker_parsing(self, parser: ZookeeperParser):
        """Test interrupting SendWorker event"""
        log_line = ZookeeperLogSamples.interrupting_sendworker()
        result = parser.parse(log_line)

        assert result["event_type"] == "worker_interrupt_send"
        assert result["template_id"] == "E25"

    def test_established_session_parsing(self, parser: ZookeeperParser):
        """Test established session event"""
        log_line = ZookeeperLogSamples.established_session()
        result = parser.parse(log_line)

        assert result["event_type"] == "session_established"
        assert result["template_id"] == "E13"
        assert result["session_id"] == "0x15678934abcdef0"
        assert result["timeout_ms"] == 30000
        assert result["remote_ip"] == "10.10.34.11"
        assert result["status"] == "success"

    def test_session_expired_parsing(self, parser: ZookeeperParser):
        """Test session expired event"""
        log_line = ZookeeperLogSamples.session_expired()
        result = parser.parse(log_line)

        assert result["event_type"] == "session_expired"
        assert result["template_id"] == "E15"
        assert result["session_id"] == "0x15678934abcdef0"
        assert result["timeout_ms"] == 30000

    def test_notification_event_parsing(self, parser: ZookeeperParser):
        """Test election notification event"""
        log_line = ZookeeperLogSamples.notification_event()
        result = parser.parse(log_line)

        assert result["event_type"] == "election_notification"
        assert result["proposed_leader"] == 1
        assert result["election_state"] == "FOLLOWING"

    def test_following_state_parsing(self, parser: ZookeeperParser):
        """Test FOLLOWING state"""
        log_line = ZookeeperLogSamples.following_state()
        result = parser.parse(log_line)

        assert result["event_type"] == "election_state_change"
        assert result["template_id"] == "E18"
        assert result["election_state"] == "FOLLOWING"

    def test_have_quorum_parsing(self, parser: ZookeeperParser):
        """Test have quorum event"""
        log_line = ZookeeperLogSamples.have_quorum()
        result = parser.parse(log_line)

        assert result["event_type"] == "quorum_achieved"
        assert result["template_id"] == "E22"
        assert result["have_quorum"] is True

    def test_cannot_open_channel_parsing(self, parser: ZookeeperParser):
        """Test cannot open channel error"""
        log_line = ZookeeperLogSamples.cannot_open_channel()
        result = parser.parse(log_line)

        assert result["event_type"] == "channel_error"
        assert result["template_id"] == "E5"
        assert result["peer_id"] == 2
        assert result["status"] == "failure"

    def test_end_of_stream_parsing(self, parser: ZookeeperParser):
        """Test end of stream exception"""
        log_line = ZookeeperLogSamples.end_of_stream()
        result = parser.parse(log_line)

        assert result["event_type"] == "end_of_stream"
        assert result["template_id"] == "E6"
        assert result["status"] == "failure"

    def test_unexpected_exception_parsing(self, parser: ZookeeperParser):
        """Test unexpected exception"""
        log_line = ZookeeperLogSamples.unexpected_exception()
        result = parser.parse(log_line)

        assert result["event_type"] == "exception_error"
        assert result["template_id"] == "E50"

    def test_server_not_running_parsing(self, parser: ZookeeperParser):
        """Test server not running error"""
        log_line = ZookeeperLogSamples.server_not_running()
        result = parser.parse(log_line)

        assert result["event_type"] == "server_not_running"
        assert result["template_id"] == "E14"
        assert result["status"] == "failure"
        assert "ZooKeeperServer not running" in result["error_reason"]

    def test_unknown_format_handling(self, parser: ZookeeperParser):
        """Test handling of unparseable logs"""
        log_line = ZookeeperLogSamples.unknown_format()
        result = parser.parse(log_line)

        assert result["event_type"] == "unknown"
        assert result["parsed_successfully"] is False
        assert result["confidence"] == 0.0


# ============================================================================
# FEATURE EXTRACTOR TESTS
# ============================================================================

class TestZookeeperFeatureExtractor:
    """Test suite for Zookeeper feature extractor"""

    @pytest.fixture
    def extractor(self) -> ZookeeperFeatureExtractor:
        """Create fresh extractor instance"""
        ext = ZookeeperFeatureExtractor()
        ext.reset_state()
        return ext

    @staticmethod
    def create_log_internal(event_dict: Dict[str, Any]) -> LogInternal:
        """Helper to create LogInternal with parsed event"""
        log = LogInternal(
            message=event_dict.get("raw_message", ""),
            server_type=ServerType.ZOOKEEPER,
            timestamp=datetime.now().isoformat(),
        )
        log.metadata = {"parsed": event_dict}
        return log

    def test_feature_extraction_single_event(self, extractor: ZookeeperFeatureExtractor):
        """Test feature extraction from a single event"""
        log = self.create_log_internal(
            ZookeeperParser().parse(ZookeeperLogSamples.received_connection_request())
        )
        features = extractor.extract(log)

        assert isinstance(features, dict)
        assert "event_count_total" in features
        assert "error_count_total" in features
        assert "anomaly_score" in features
        assert features["event_count_total"] == 1.0
        assert features["error_count_total"] == 0.0

    def test_connection_tracking(self, extractor: ZookeeperFeatureExtractor):
        """Test connection event tracking"""
        parser = ZookeeperParser()

        # Received connection
        log1 = self.create_log_internal(
            parser.parse(ZookeeperLogSamples.received_connection_request())
        )
        features1 = extractor.extract(log1)

        # Connection broken
        log2 = self.create_log_internal(
            parser.parse(ZookeeperLogSamples.connection_broken())
        )
        features2 = extractor.extract(log2)

        assert features1["connection_received_count"] == 1.0
        assert features2["connection_broken_count"] == 1.0
        assert features2["connection_break_rate"] == 0.5

    def test_connection_burst_detection(self, extractor: ZookeeperFeatureExtractor):
        """Test detection of connection break bursts"""
        parser = ZookeeperParser()

        # Add 5 consecutive connection breaks
        breaks = [
            ZookeeperLogSamples.connection_broken_cascade_1(),
            ZookeeperLogSamples.connection_broken_cascade_2(),
            ZookeeperLogSamples.connection_broken_cascade_3(),
            ZookeeperLogSamples.connection_broken_cascade_4(),
            ZookeeperLogSamples.connection_broken_cascade_5(),
        ]

        for break_log in breaks:
            log = self.create_log_internal(parser.parse(break_log))
            features = extractor.extract(log)

        # Should detect burst
        assert features["connection_consecutive_breaks_max"] == 5.0
        assert features["anomaly_connection_burst"] == 1.0

    def test_worker_churn_tracking(self, extractor: ZookeeperFeatureExtractor):
        """Test worker churn detection"""
        parser = ZookeeperParser()

        worker_logs = [
            ZookeeperLogSamples.send_worker_leaving(),
            ZookeeperLogSamples.interrupted_waiting(),
            ZookeeperLogSamples.interrupting_sendworker(),
        ]

        for log_line in worker_logs:
            log = self.create_log_internal(parser.parse(log_line))
            extractor.extract(log)

        # Should have tracked worker activity
        assert extractor.worker_send_leaves > 0
        assert extractor.worker_interruptions > 0

    def test_session_tracking(self, extractor: ZookeeperFeatureExtractor):
        """Test session establishment and expiration"""
        parser = ZookeeperParser()

        # Session established
        log1 = self.create_log_internal(
            parser.parse(ZookeeperLogSamples.established_session())
        )
        features1 = extractor.extract(log1)

        # Session expired
        log2 = self.create_log_internal(
            parser.parse(ZookeeperLogSamples.session_expired())
        )
        features2 = extractor.extract(log2)

        assert features1["session_established_count"] == 1.0
        assert features2["session_expired_count"] == 1.0
        assert features2["session_success_rate"] == 0.5

    def test_quorum_tracking(self, extractor: ZookeeperFeatureExtractor):
        """Test quorum/election event tracking"""
        parser = ZookeeperParser()

        election_logs = [
            ZookeeperLogSamples.notification_timeout(),
            ZookeeperLogSamples.new_election(),
            ZookeeperLogSamples.notification_event(),
            ZookeeperLogSamples.have_quorum(),
            ZookeeperLogSamples.following_state(),
        ]

        for log_line in election_logs:
            log = self.create_log_internal(parser.parse(log_line))
            extractor.extract(log)

        # Should track election events
        assert extractor.election_notifications > 0
        assert extractor.have_quorum_count > 0
        assert extractor.election_state_changes > 0

    def test_error_cascade_detection(self, extractor: ZookeeperFeatureExtractor):
        """Test error cascade detection (5+ consecutive errors)"""
        parser = ZookeeperParser()

        # 5 connection breaks = error cascade
        breaks = [
            ZookeeperLogSamples.connection_broken_cascade_1(),
            ZookeeperLogSamples.connection_broken_cascade_2(),
            ZookeeperLogSamples.connection_broken_cascade_3(),
            ZookeeperLogSamples.connection_broken_cascade_4(),
            ZookeeperLogSamples.connection_broken_cascade_5(),
        ]

        for break_log in breaks:
            log = self.create_log_internal(parser.parse(break_log))
            features = extractor.extract(log)

        # Should detect error cascade
        assert features["error_cascade_indicator"] == 1.0

    def test_error_tracking(self, extractor: ZookeeperFeatureExtractor):
        """Test general error tracking"""
        parser = ZookeeperParser()

        error_logs = [
            ZookeeperLogSamples.cannot_open_channel(),
            ZookeeperLogSamples.end_of_stream(),
            ZookeeperLogSamples.server_not_running(),
        ]

        for log_line in error_logs:
            log = self.create_log_internal(parser.parse(log_line))
            extractor.extract(log)

        # Should track errors
        assert extractor.error_events >= 2
        assert len(extractor.error_types) > 0

    def test_feature_vector_completeness(self, extractor: ZookeeperFeatureExtractor):
        """Test that feature vector contains expected keys"""
        log = self.create_log_internal(
            ZookeeperParser().parse(ZookeeperLogSamples.received_connection_request())
        )
        features = extractor.extract(log)

        # Check major feature categories
        assert "event_count_total" in features
        assert "connection_received_count" in features
        assert "worker_send_leaves_count" in features
        assert "session_established_count" in features
        assert "election_notification_count" in features
        assert "error_count_total" in features
        assert "anomaly_score" in features

    def test_singleton_state_preservation(self):
        """Test that extractor singleton preserves state"""
        ext1 = get_zookeeper_feature_extractor()
        ext2 = get_zookeeper_feature_extractor()

        # Both should be same instance
        assert ext1 is ext2

        # State should be preserved
        parser = ZookeeperParser()
        log = self.create_log_internal(
            parser.parse(ZookeeperLogSamples.received_connection_request())
        )
        features1 = ext1.extract(log)
        features2 = ext2.extract(log)

        # State should accumulate
        assert features2["event_count_total"] == 2.0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestParserFeatureIntegration:
    """Test integration between parser and feature extractor"""

    def test_end_to_end_pipeline(self):
        """Test complete parsing and feature extraction pipeline"""
        parser = ZookeeperParser()
        extractor = ZookeeperFeatureExtractor()
        extractor.reset_state()

        log_lines = [
            ZookeeperLogSamples.received_connection_request(),
            ZookeeperLogSamples.established_session(),
            ZookeeperLogSamples.notification_event(),
            ZookeeperLogSamples.have_quorum(),
        ]

        for log_line in log_lines:
            # Parse
            parsed = parser.parse(log_line)
            assert parsed["parsed_successfully"] is True

            # Create log internal
            log = LogInternal(
                message=log_line,
                server_type=ServerType.ZOOKEEPER,
                timestamp=datetime.now().isoformat(),
            )
            log.metadata = {"parsed": parsed}

            # Extract features
            features = extractor.extract(log)
            assert isinstance(features, dict)
            assert "anomaly_score" in features

    def test_connection_failure_anomaly_detection(self):
        """Test anomaly detection for connection failures"""
        parser = ZookeeperParser()
        extractor = ZookeeperFeatureExtractor()
        extractor.reset_state()

        # Simulate connection failure scenario
        failure_logs = [
            ZookeeperLogSamples.cannot_open_channel(),
            ZookeeperLogSamples.connection_broken_cascade_1(),
            ZookeeperLogSamples.connection_broken_cascade_2(),
            ZookeeperLogSamples.connection_broken_cascade_3(),
            ZookeeperLogSamples.connection_broken_cascade_4(),
        ]

        for log_line in failure_logs:
            parsed = parser.parse(log_line)
            log = LogInternal(
                message=log_line,
                server_type=ServerType.ZOOKEEPER,
                timestamp=datetime.now().isoformat(),
            )
            log.metadata = {"parsed": parsed}
            features = extractor.extract(log)

        # Final features should show anomaly
        assert features["connection_consecutive_breaks_max"] >= 4
        assert features["anomaly_connection_burst"] == 1.0 or features["anomaly_error_cascade"] == 1.0

    def test_election_event_sequence(self):
        """Test proper handling of election event sequences"""
        parser = ZookeeperParser()
        extractor = ZookeeperFeatureExtractor()
        extractor.reset_state()

        election_sequence = [
            ZookeeperLogSamples.notification_timeout(),
            ZookeeperLogSamples.new_election(),
            ZookeeperLogSamples.notification_event(),
            ZookeeperLogSamples.have_quorum(),
            ZookeeperLogSamples.following_state(),
            ZookeeperLogSamples.leader_election_took(),
        ]

        for log_line in election_sequence:
            parsed = parser.parse(log_line)
            log = LogInternal(
                message=log_line,
                server_type=ServerType.ZOOKEEPER,
                timestamp=datetime.now().isoformat(),
            )
            log.metadata = {"parsed": parsed}
            features = extractor.extract(log)

        # Election should complete with quorum
        assert features["have_quorum_count"] >= 1
        assert features["election_state_change_count"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
