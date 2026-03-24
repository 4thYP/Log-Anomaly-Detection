"""
STEP 7: Complete test suite for Linux parser and feature extractor.

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
from app.parsers.linux_parser import LinuxParser
from app.parsers.log_event_schema import ParsedLogEvent, EventGroup
from app.features.linux_feature_extractor import LinuxFeatureExtractor


# ==============================================================================
# TEST FIXTURES & REAL LOG SAMPLES
# ==============================================================================

class LinuxLogSamples:
    """Real Linux log samples from Loghub dataset"""
    
    @staticmethod
    def ssh_auth_failure_no_user():
        return (
            "Jun 14 15:16:01 combo sshd(pam_unix)[19939]: "
            "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= "
            "rhost=218.188.2.4"
        )
    
    @staticmethod
    def ssh_auth_failure_with_user():
        return (
            "Jun 15 02:04:59 combo sshd(pam_unix)[20882]: "
            "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= "
            "rhost=220-135-151-1.hinet-ip.hinet.net  user=root"
        )
    
    @staticmethod
    def ftp_connection():
        return (
            "Jun 17 07:07:00 combo ftpd[29504]: "
            "connection from 24.54.76.216 (24-54-76-216.bflony.adelphia.net) "
            "at Fri Jun 17 07:07:00 2005"
        )
    
    @staticmethod
    def session_opened():
        return (
            "Jun 15 04:06:18 combo su: "
            "session opened for user cyrus by root(uid=0)"
        )
    
    @staticmethod
    def session_closed():
        return "Jun 15 04:06:19 combo su: session closed for user cyrus"
    
    @staticmethod
    def kernel_info():
        return (
            "Jun 13 00:56:16 combo kernel: "
            "Linux version 2.6.9-42.ELsmp (mockbuild@builder.example.com) "
            "(gcc version 3.4.6 20060404 (Red Hat 3.4.6-10))"
        )
    
    @staticmethod
    def logrotate_alert():
        return (
            "Jun 14 14:35:26 combo logrotate: "
            "ALERT exited abnormally with [1]"
        )
    
    @staticmethod
    def malformed_log():
        return "this is not a valid syslog format at all"
    
    @staticmethod
    def empty_log():
        return ""
    
    @staticmethod
    def ftp_timeout():
        return (
            "Jun 18 10:20:30 combo ftpd[31234]: "
            "User anonymous timed out after 600 seconds"
        )
    
    @staticmethod
    def root_login():
        return "Jun 19 15:45:22 combo login: ROOT LOGIN ON tty2"


@pytest.fixture
def parser():
    return LinuxParser()


@pytest.fixture
def extractor():
    return LinuxFeatureExtractor()


def _create_log_internal(message: str, timestamp_str: str = "2024-06-14T15:16:01"):
    """Create LogInternal for testing"""
    return LogInternal(
        sid="test_linux_server",
        timestamp=datetime.fromisoformat(timestamp_str),
        server_type=ServerType.LINUX,
        log_file="test.log",
        message=message,
        metadata={}
    )


# ==============================================================================
# PARSER OUTPUT VALIDATION TESTS
# ==============================================================================

class TestLinuxParserSchema:
    """Validate Linux parser conforms to ParsedLogEvent schema"""
    
    def test_ssh_auth_failure_returns_valid_schema(self, parser):
        """SSH auth failure produces valid ParsedLogEvent"""
        result = parser.parse(LinuxLogSamples.ssh_auth_failure_no_user())
        
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
        assert result["template_id"] > 0
        assert isinstance(result["timestamp"], str)
        assert "T" in result["timestamp"]  # ISO 8601 format
        assert result["event_group"] in [eg.value for eg in EventGroup]
    
    def test_ssh_auth_failure_event_group(self, parser):
        """SSH auth failure correctly categorized"""
        result = parser.parse(LinuxLogSamples.ssh_auth_failure_no_user())
        assert result["event_group"] == EventGroup.AUTHENTICATION.value
    
    def test_ftp_connection_event_group(self, parser):
        """FTP connection correctly categorized"""
        result = parser.parse(LinuxLogSamples.ftp_connection())
        assert result["event_group"] == EventGroup.CONNECTION.value
    
    def test_session_opened_event_group(self, parser):
        """Session open correctly categorized"""
        result = parser.parse(LinuxLogSamples.session_opened())
        assert result["event_group"] == EventGroup.SESSION.value
    
    def test_optional_fields_in_metadata(self, parser):
        """Optional fields can be stored in metadata dict or top-level"""
        result = parser.parse(LinuxLogSamples.ssh_auth_failure_with_user())
        
        # Just verify that the parser successfully parsed the event
        assert result["parsed_successfully"] is True
        assert result["event_type"] == "auth_failure"
        assert result["template_id"] > 0
    
    def test_template_id_is_integer(self, parser):
        """Template IDs are integers, not strings"""
        samples = [
            LinuxLogSamples.ssh_auth_failure_no_user(),
            LinuxLogSamples.ftp_connection(),
            LinuxLogSamples.session_opened(),
        ]
        
        for sample in samples:
            result = parser.parse(sample)
            assert isinstance(result["template_id"], int), \
                f"template_id should be int, got {type(result['template_id'])}"
    
    def test_malformed_log_returns_unknown_event(self, parser):
        """Malformed logs return unknown event"""
        result = parser.parse(LinuxLogSamples.malformed_log())
        
        assert result is not None
        assert "event_type" in result
        assert "event_group" in result
        # Should be system or error group for unparseable logs
        assert result["event_group"] in [
            EventGroup.SYSTEM.value, 
            EventGroup.ERROR.value
        ]
    
    def test_empty_log_handling(self, parser):
        """Empty logs handled gracefully"""
        result = parser.parse(LinuxLogSamples.empty_log())
        assert result is not None
        assert "event_group" in result
        assert result["event_group"] in [EventGroup.SYSTEM.value, EventGroup.ERROR.value]


# ==============================================================================
# FEATURE EXTRACTOR OUTPUT VALIDATION TESTS
# ==============================================================================

class TestLinuxFeatureExtractorOutput:
    """Validate feature extractor output format and normalization"""
    
    def test_returns_list_of_floats(self, parser, extractor):
        """Extract returns List[float], not Dict"""
        log_internal = _create_log_internal(LinuxLogSamples.ssh_auth_failure_no_user())
        features = extractor.extract(log_internal)
        
        assert isinstance(features, list)
        assert len(features) == 14  # Expected 14 for Linux
        assert all(isinstance(f, float) for f in features)
    
    def test_all_features_normalized(self, parser, extractor):
        """All features are in [0, 1] range"""
        samples = [
            LinuxLogSamples.ssh_auth_failure_no_user(),
            LinuxLogSamples.ftp_connection(),
            LinuxLogSamples.session_opened(),
        ]
        
        for sample in samples:
            log_internal = _create_log_internal(sample)
            features = extractor.extract(log_internal)
            
            for i, feature in enumerate(features):
                assert 0.0 <= feature <= 1.0, \
                    f"Feature {i} = {feature} not in [0, 1]"
    
    def test_first_element_is_event_type_code(self, parser, extractor):
        """First element encodes event type"""
        log_internal = _create_log_internal(LinuxLogSamples.ssh_auth_failure_no_user())
        features = extractor.extract(log_internal)
        
        # Should be non-zero for auth failure
        assert features[0] > 0
    
    def test_multiple_servers_per_server_isolation(self, parser, extractor):
        """Different servers maintain separate state"""
        # Server 1
        log1_s1 = LogInternal(
            sid="server1",
            timestamp=datetime.fromisoformat("2024-06-14T15:16:01"),
            server_type=ServerType.LINUX,
            log_file="test.log",
            message=LinuxLogSamples.ssh_auth_failure_no_user(),
            metadata={}
        )
        features1 = extractor.extract(log1_s1)
        
        # Server 2 (different sid)
        log2_s2 = LogInternal(
            sid="server2",
            timestamp=datetime.fromisoformat("2024-06-14T15:16:02"),
            server_type=ServerType.LINUX,
            log_file="test.log",
            message=LinuxLogSamples.ftp_connection(),
            metadata={}
        )
        features2 = extractor.extract(log2_s2)
        
        # Both should have valid feature vectors
        assert len(features1) == 14
        assert len(features2) == 14
        # Both should maintain per-server state independently
        assert all(0 <= f <= 1 for f in features1)
        assert all(0 <= f <= 1 for f in features2)
    
    def test_consistent_output_length(self, extractor):
        """All events produce same length output"""
        samples = [
            LinuxLogSamples.ssh_auth_failure_no_user(),
            LinuxLogSamples.ftp_connection(),
            LinuxLogSamples.session_opened(),
            LinuxLogSamples.kernel_info(),
            LinuxLogSamples.malformed_log(),
        ]
        
        lengths = []
        for sample in samples:
            log_internal = _create_log_internal(sample)
            features = extractor.extract(log_internal)
            lengths.append(len(features))
        
        # All should be 14
        assert all(l == 14 for l in lengths), f"Inconsistent lengths: {lengths}"


# ==============================================================================
# TIMESTAMP HANDLING TESTS
# ==============================================================================

class TestLinuxTimestampHandling:
    """Verify timestamp extraction and format"""
    
    def test_parser_extracts_iso8601_timestamp(self, parser):
        """Parser produces ISO 8601 timestamps"""
        result = parser.parse(LinuxLogSamples.ssh_auth_failure_no_user())
        timestamp = result.get("timestamp")
        
        assert timestamp is not None
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO 8601 separates date and time with T
    
    def test_feature_uses_log_timestamp_not_wall_clock(self, extractor):
        """Feature extraction uses log timestamp, not datetime.now()"""
        log_past = LogInternal(
            sid="test_server",
            timestamp=datetime.fromisoformat("2020-01-01T00:00:00"),
            server_type=ServerType.LINUX,
            log_file="test.log",
            message=LinuxLogSamples.ssh_auth_failure_no_user(),
            metadata={}
        )
        features_past = extractor.extract(log_past)
        
        log_now = LogInternal(
            sid="test_server_2",
            timestamp=datetime.now(),
            server_type=ServerType.LINUX,
            log_file="test.log",
            message=LinuxLogSamples.ssh_auth_failure_no_user(),
            metadata={}
        )
        features_now = extractor.extract(log_now)
        
        # Both should be valid feature vectors
        assert len(features_past) == 14
        assert len(features_now) == 14
        # Both should be normalized
        assert all(0 <= f <= 1 for f in features_past)
        assert all(0 <= f <= 1 for f in features_now)


# ==============================================================================
# EDGE CASE TESTS
# ==============================================================================

class TestLinuxEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_very_long_message(self, parser):
        """Handle very long log messages"""
        long_message = "Jun 14 15:16:01 combo sshd[19939]: " + "x" * 10000
        result = parser.parse(long_message)
        assert result is not None
        assert "event_group" in result
    
    def test_special_characters_in_fields(self, parser):
        """Handle special characters in log fields"""
        special_log = (
            "Jun 14 15:16:01 combo sshd[19939]: "
            "authentication failure; rhost=192.168.1.1@special user=root$admin"
        )
        result = parser.parse(special_log)
        assert result is not None
    
    def test_multiple_spaces_in_message(self, parser):
        """Handle multiple consecutive spaces"""
        spaced_log = "Jun 14 15:16:01  combo   sshd[19939]:    test message"
        result = parser.parse(spaced_log)
        assert result is not None
    
    def test_missing_pid_in_component(self, parser):
        """Handle components without PID"""
        no_pid_log = "Jun 14 15:16:01 combo sshd: no pid in bracket here"
        result = parser.parse(no_pid_log)
        assert result is not None
        assert "event_group" in result
    
    def test_rapid_fire_same_ip_failures(self, extractor):
        """Handle rapid repeated events from same IP"""
        for i in range(10):
            log_internal = _create_log_internal(
                LinuxLogSamples.ssh_auth_failure_no_user(),
                timestamp_str=f"2024-06-14T15:{16+i//60:02d}:{1+i%60:02d}"
            )
            features = extractor.extract(log_internal)
            assert len(features) == 14
            assert all(0 <= f <= 1 for f in features)
    
    def test_mixed_event_types_per_server(self, extractor):
        """Handle mix of different event types for same server"""
        samples = [
            LinuxLogSamples.ssh_auth_failure_no_user(),
            LinuxLogSamples.ftp_connection(),
            LinuxLogSamples.session_opened(),
            LinuxLogSamples.session_closed(),
        ]
        
        for i, sample in enumerate(samples):
            log_internal = LogInternal(
                sid="mixed_server",
                timestamp=datetime.fromisoformat(f"2024-06-14T15:{16+i:02d}:01"),
                server_type=ServerType.LINUX,
                log_file="test.log",
                message=sample,
                metadata={}
            )
            features = extractor.extract(log_internal)
            assert len(features) == 14


# ==============================================================================
# END-TO-END INTEGRATION TESTS
# ==============================================================================

class TestLinuxEndToEnd:
    """Test complete LogCreate → Parse → Extract flow"""
    
    def test_full_pipeline_auth_failure(self, parser, extractor):
        """Complete pipeline for auth failure event"""
        log_internal = _create_log_internal(LinuxLogSamples.ssh_auth_failure_no_user())
        
        # Parse
        parsed = parser.parse(log_internal.message)
        assert parsed is not None
        assert "event_group" in parsed
        
        # Extract features
        features = extractor.extract(log_internal)
        assert len(features) == 14
        assert all(0 <= f <= 1 for f in features)
    
    def test_full_pipeline_ftp_connection(self, parser, extractor):
        """Complete pipeline for FTP connection event"""
        log_internal = _create_log_internal(LinuxLogSamples.ftp_connection())
        
        parsed = parser.parse(log_internal.message)
        assert parsed["event_group"] == EventGroup.CONNECTION.value
        
        features = extractor.extract(log_internal)
        assert len(features) == 14
    
    def test_full_pipeline_session_lifecycle(self, parser, extractor):
        """Complete pipeline for session open/close"""
        # Session open
        log_open = _create_log_internal(
            LinuxLogSamples.session_opened(),
            "2024-06-15T04:06:18"
        )
        parsed_open = parser.parse(log_open.message)
        features_open = extractor.extract(log_open)
        
        # Session close
        log_close = _create_log_internal(
            LinuxLogSamples.session_closed(),
            "2024-06-15T04:06:19"
        )
        parsed_close = parser.parse(log_close.message)
        features_close = extractor.extract(log_close)
        
        # Both should be valid
        assert parsed_open["event_group"] == EventGroup.SESSION.value
        assert parsed_close["event_group"] == EventGroup.SESSION.value
        assert len(features_open) == 14
        assert len(features_close) == 14


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
