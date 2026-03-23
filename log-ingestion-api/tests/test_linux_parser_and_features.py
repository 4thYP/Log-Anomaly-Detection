"""
Comprehensive test cases for Linux parser and feature extractor.

Each test case includes:
1. Raw log line
2. Expected parsed output
3. Expected features (after state updates)
"""

import pytest
from datetime import datetime
from app.parsers.linux_parser import LinuxParser
from app.features.linux_feature_extractor import LinuxFeatureExtractor


# ============================================================================
# TEST CASE 1: SSH Authentication Failure (No User Specified)
# ============================================================================

TEST_CASE_1_RAW = (
    "Jun 14 15:16:01 combo sshd(pam_unix)[19939]: "
    "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= "
    "rhost=218.188.2.4"
)

TEST_CASE_1_EXPECTED_PARSED = {
    "event_type": "auth_failure",
    "component": "sshd",
    "template_id": "E16",
    "template": "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*>",
    "user": None,
    "ip": "218.188.2.4",
    "status": "failure",
    "pid": 19939,
    "uid": 0,
    "parsed_successfully": True,
    "confidence": 1.0,
}

TEST_CASE_1_EXPECTED_FEATURES = {
    "event_type_code": 1,  # AUTH_FAILURE
    "component_code": 1,   # sshd
    "auth_failures_5m": 1.0,
    "auth_failures_10m": 1.0,
    "ftp_events_5m": 0.0,
    "ftp_events_10m": 0.0,
    "event_count_5m": 1.0,
    "event_count_10m": 1.0,
    "auth_failure_rate_5m": 1.0,
    "ftp_event_rate_5m": 0.0,
    "ip_age_seconds": 0.0,  # First time seeing this IP
    "is_new_ip": 1.0,
    "ip_events_5m": 1.0,
    "ip_events_10m": 1.0,
    "ip_total_auth_failures": 1.0,
    "ip_failure_streak": 1.0,
    "ip_ftp_connections": 0.0,
    "ip_active_sessions": 0.0,
    "ip_failure_rate": 1.0,
    "active_session_count": 0.0,
    "unique_users_with_sessions": 0.0,
    "avg_session_duration": 0.0,
    "max_session_duration": 0.0,
    "is_auth_failure": 1.0,
    "auth_failure_from_new_ip": 1.0,
    "auth_failure_from_new_user": 0.0,  # No user specified
    "is_ftp_timeout": 0.0,
    "is_session_open": 0.0,
    "is_session_close": 0.0,
    "ip_high_failure_streak": 0.0,  # Streak is 1, not >= 5
    "multiple_new_ips": 0.0,
    "ftp_burst_detected": 0.0,
    "user_low_success_rate": 0.0,
    "high_failure_frequency": 0.0,
    "anomaly_score": 0.0,  # No indicators triggered
}


# ============================================================================
# TEST CASE 2: SSH Authentication Failure with User (Brute Force Indicator)
# ============================================================================

TEST_CASE_2_RAW = (
    "Jun 15 02:04:59 combo sshd(pam_unix)[20882]: "
    "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= "
    "rhost=220-135-151-1.hinet-ip.hinet.net  user=root"
)

TEST_CASE_2_EXPECTED_PARSED = {
    "event_type": "auth_failure",
    "component": "sshd",
    "template_id": "E18",
    "template": "authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*>  user=root",
    "user": "root",
    "ip": "220-135-151-1.hinet-ip.hinet.net",
    "status": "failure",
    "pid": 20882,
    "uid": 0,
    "parsed_successfully": True,
    "confidence": 1.0,
}

TEST_CASE_2_EXPECTED_FEATURES = {
    "event_type_code": 1,  # AUTH_FAILURE
    "component_code": 1,   # sshd
    # Time windows will include previous test case events if run sequentially
    # For isolated test, expect:
    "ip_total_auth_failures": 1.0,
    "ip_failure_streak": 1.0,
    "is_auth_failure": 1.0,
    "auth_failure_from_new_ip": 1.0,  # New IP
    "auth_failure_from_new_user": 1.0,  # New user "root"
    "user_events_5m": 1.0,
    "user_auth_failures": 1.0,
    "user_successful_logins": 0.0,
    "user_success_rate": 0.0,
    "is_new_user": 1.0,
    "anomaly_score": 0.0,  # Single event not yet anomalous
}


# ============================================================================
# TEST CASE 3: FTP Connection Burst (Anomaly)
# ============================================================================

TEST_CASE_3_RAW = (
    "Jun 17 07:07:00 combo ftpd[29504]: "
    "connection from 24.54.76.216 (24-54-76-216.bflony.adelphia.net) "
    "at Fri Jun 17 07:07:00 2005"
)

TEST_CASE_3_EXPECTED_PARSED = {
    "event_type": "ftp_connect",
    "component": "ftpd",
    "template_id": "E29",
    "template": "connection from <*> (<*>) at <*>:<*>:<*>",
    "ip": "24.54.76.216",
    "hostname": "24-54-76-216.bflony.adelphia.net",
    "status": "connect",
    "pid": 29504,
    "parsed_successfully": True,
    "confidence": 1.0,
}

TEST_CASE_3_EXPECTED_FEATURES_SINGLE = {
    "event_type_code": 6,  # FTP_CONNECT
    "component_code": 4,   # ftpd
    "ftp_events_5m": 1.0,
    "ftp_events_10m": 1.0,
    "ftp_event_rate_5m": 1.0,  # Only FTP event in window
    "ip_ftp_connections": 1.0,
    "ip_events_5m": 1.0,
    "ip_high_failure_streak": 0.0,  # No auth failures from this IP
    "ftp_burst_detected": 0.0,  # Only 1 connection, not > 5
    "anomaly_score": 0.0,
}

TEST_CASE_3_EXPECTED_FEATURES_BURST = {
    # After 6+ FTP connections from same IP within 5m
    "event_type_code": 6,
    "ip_ftp_connections": 6.0,  # >= 6 connections
    "ftp_burst_detected": 1.0,
    "anomaly_score": 0.25,  # Burst indicator triggered
}


# ============================================================================
# TEST CASE 4: Session Open/Close Pair
# ============================================================================

TEST_CASE_4A_RAW = (
    "Jun 15 04:06:18 combo su(pam_unix)[21416]: "
    "session opened for user cyrus by (uid=0)"
)

TEST_CASE_4A_EXPECTED_PARSED = {
    "event_type": "session_opened",
    "component": "su",
    "template_id": "E102",
    "template": "session opened for user <*> by (uid=<*>)",
    "user": "cyrus",
    "status": "success",
    "uid": 0,
    "pid": 21416,
    "parsed_successfully": True,
}

TEST_CASE_4B_RAW = (
    "Jun 15 04:06:19 combo su(pam_unix)[21416]: "
    "session closed for user cyrus"
)

TEST_CASE_4B_EXPECTED_PARSED = {
    "event_type": "session_closed",
    "component": "su",
    "template_id": "E101",
    "template": "session closed for user <*>",
    "user": "cyrus",
    "status": "closed",
    "pid": 21416,
    "parsed_successfully": True,
}

TEST_CASE_4_EXPECTED_FEATURES_AFTER_BOTH = {
    # After both open and close
    "event_type_code": 5,  # SESSION_CLOSED (last event)
    "active_session_count": 0.0,  # Closed
    "unique_users_with_sessions": 0.0,  # User no longer has active session
    "user_successful_logins": 1.0,
    "is_session_close": 1.0,
    # Session duration should be ~1 second
    "avg_session_duration": 1.0,  # Approximate
    "max_session_duration": 1.0,
}


# ============================================================================
# TEST CASE 5: Logrotate Alert
# ============================================================================

TEST_CASE_5_RAW = "Jun 15 04:06:20 combo logrotate: ALERT exited abnormally with [1]"

TEST_CASE_5_EXPECTED_PARSED = {
    "event_type": "alert",
    "component": "logrotate",
    "template_id": "E8",
    "template": "ALERT exited abnormally with [1]",
    "status": "abnormal_exit",
    "exit_code": 1,
    "parsed_successfully": True,
}

TEST_CASE_5_EXPECTED_FEATURES = {
    "event_type_code": 9,  # ALERT
    "component_code": 5,   # logrotate
    "is_auth_failure": 0.0,
    "is_ftp_timeout": 0.0,
    "is_session_open": 0.0,
    "is_session_close": 0.0,
    "anomaly_score": 0.0,  # Service alerts are expected
}


# ============================================================================
# TEST CASE 6: SSH "Check Pass" Event
# ============================================================================

TEST_CASE_6_RAW = (
    "Jun 14 15:16:02 combo sshd(pam_unix)[19937]: check pass; user unknown"
)

TEST_CASE_6_EXPECTED_PARSED = {
    "event_type": "auth_check",
    "component": "sshd",
    "template_id": "E27",
    "template": "check pass; user unknown",
    "status": "check_pass",
    "pid": 19937,
    "parsed_successfully": True,
}


# ============================================================================
# PYTEST TEST FUNCTIONS
# ============================================================================


class TestLinuxParser:
    """Test cases for LinuxParser"""

    def setup_method(self):
        """Initialize parser before each test"""
        self.parser = LinuxParser()

    def test_ssh_auth_failure_no_user(self):
        """Test Case 1: SSH auth failure without user specification"""
        result = self.parser.parse(TEST_CASE_1_RAW)

        assert result["event_type"] == TEST_CASE_1_EXPECTED_PARSED["event_type"]
        assert result["component"] == TEST_CASE_1_EXPECTED_PARSED["component"]
        assert result["template_id"] == TEST_CASE_1_EXPECTED_PARSED["template_id"]
        assert result["ip"] == TEST_CASE_1_EXPECTED_PARSED["ip"]
        assert result["status"] == TEST_CASE_1_EXPECTED_PARSED["status"]
        assert result["pid"] == TEST_CASE_1_EXPECTED_PARSED["pid"]
        assert result["parsed_successfully"] is True

    def test_ssh_auth_failure_with_root_user(self):
        """Test Case 2: SSH auth failure with root user (brute force indicator)"""
        result = self.parser.parse(TEST_CASE_2_RAW)

        assert result["event_type"] == "auth_failure"
        assert result["user"] == "root"
        assert result["template_id"] == "E18"
        assert "220-135-151-1.hinet-ip.hinet.net" in result["ip"]

    def test_ftp_connection(self):
        """Test Case 3: FTP connection event"""
        result = self.parser.parse(TEST_CASE_3_RAW)

        assert result["event_type"] == "ftp_connect"
        assert result["component"] == "ftpd"
        assert result["template_id"] == "E29"
        assert result["ip"] == "24.54.76.216"
        assert result["hostname"] == "24-54-76-216.bflony.adelphia.net"

    def test_session_opened(self):
        """Test Case 4a: Session opened event"""
        result = self.parser.parse(TEST_CASE_4A_RAW)

        assert result["event_type"] == "session_opened"
        assert result["user"] == "cyrus"
        assert result["status"] == "success"
        assert result["uid"] == 0

    def test_session_closed(self):
        """Test Case 4b: Session closed event"""
        result = self.parser.parse(TEST_CASE_4B_RAW)

        assert result["event_type"] == "session_closed"
        assert result["user"] == "cyrus"
        assert result["status"] == "closed"

    def test_logrotate_alert(self):
        """Test Case 5: Logrotate service alert"""
        result = self.parser.parse(TEST_CASE_5_RAW)

        assert result["event_type"] == "alert"
        assert result["component"] == "logrotate"
        assert result["exit_code"] == 1
        assert result["status"] == "abnormal_exit"

    def test_ssh_check_pass(self):
        """Test Case 6: SSH check pass event"""
        result = self.parser.parse(TEST_CASE_6_RAW)

        assert result["event_type"] == "auth_check"
        assert result["template_id"] == "E27"
        assert result["status"] == "check_pass"


class TestLinuxFeatureExtractor:
    """Test cases for LinuxFeatureExtractor"""

    def setup_method(self):
        """Initialize parser and extractor before each test"""
        self.parser = LinuxParser()
        self.extractor = LinuxFeatureExtractor()

    def test_features_first_auth_failure(self):
        """Test single auth failure event features"""
        parsed = self.parser.parse(TEST_CASE_1_RAW)
        self.extractor.current_timestamp = datetime(2024, 6, 14, 15, 16, 1)
        features = self.extractor._extract_features(parsed)

        assert features["event_type_code"] == 1  # AUTH_FAILURE
        assert features["is_auth_failure"] == 1.0
        assert features["is_new_ip"] == 1.0
        assert features["ip_failure_streak"] == 1.0
        assert features["anomaly_score"] == 0.0  # Single event

    def test_features_ftp_connection(self):
        """Test FTP connection features"""
        parsed = self.parser.parse(TEST_CASE_3_RAW)
        self.extractor.current_timestamp = datetime(2024, 6, 17, 7, 7, 0)
        features = self.extractor._extract_features(parsed)

        assert features["event_type_code"] == 6  # FTP_CONNECT
        assert features["is_new_ip"] == 1.0
        assert features["ftp_burst_detected"] == 0.0  # Single connection

    def test_features_session_management(self):
        """Test session open/close feature tracking"""
        # Open session
        parsed_open = self.parser.parse(TEST_CASE_4A_RAW)
        self.extractor.current_timestamp = datetime(2024, 6, 15, 4, 6, 18)
        features_open = self.extractor._extract_features(parsed_open)

        assert features_open["active_session_count"] == 1.0
        assert features_open["is_session_open"] == 1.0

        # Close session
        parsed_close = self.parser.parse(TEST_CASE_4B_RAW)
        self.extractor.current_timestamp = datetime(2024, 6, 15, 4, 6, 19)
        features_close = self.extractor._extract_features(parsed_close)

        assert features_close["active_session_count"] == 0.0
        assert features_close["is_session_close"] == 1.0
        # Should track session duration
        assert features_close["avg_session_duration"] == 1.0

    def test_features_repeated_auth_failures_indicator(self):
        """Test anomaly indicator: repeated auth failures"""
        self.extractor.current_timestamp = datetime(2024, 6, 15, 12, 12, 34)

        # Simulate 5 auth failures from same IP
        for i in range(5):
            parsed = self.parser.parse(TEST_CASE_1_RAW)
            features = self.extractor._extract_features(parsed)
            self.extractor.current_timestamp = datetime(
                2024, 6, 15, 12, 12, 34 + i
            )

        # After 5 failures, streak should be >= 5
        parsed = self.parser.parse(TEST_CASE_1_RAW)
        features = self.extractor._extract_features(parsed)

        assert features["ip_failure_streak"] >= 5.0
        assert features["ip_high_failure_streak"] == 1.0
        assert features["anomaly_score"] > 0.0

    def test_feature_extraction_encoding(self):
        """Test event type and component encoding"""
        parsed = self.parser.parse(TEST_CASE_1_RAW)
        features = self.extractor._extract_features(parsed)

        # Check encoding values
        assert features["event_type_code"] == 1  # AUTH_FAILURE
        assert features["component_code"] == 1  # sshd

        parsed_ftp = self.parser.parse(TEST_CASE_3_RAW)
        features_ftp = self.extractor._extract_features(parsed_ftp)
        assert features_ftp["event_type_code"] == 6  # FTP_CONNECT
        assert features_ftp["component_code"] == 4  # ftpd

    def test_state_summary(self):
        """Test internal state inspection"""
        # Add some events
        parsed1 = self.parser.parse(TEST_CASE_1_RAW)
        self.extractor.current_timestamp = datetime(2024, 6, 14, 15, 16, 1)
        self.extractor._extract_features(parsed1)

        parsed2 = self.parser.parse(TEST_CASE_3_RAW)
        self.extractor.current_timestamp = datetime(2024, 6, 17, 7, 7, 0)
        self.extractor._extract_features(parsed2)

        state = self.extractor.get_state_summary()

        assert state["total_events"] == 2
        assert state["unique_ips"] >= 1
        assert state["total_auth_failures"] >= 1
        assert state["total_ftp_events"] >= 1


# ============================================================================
# EXAMPLE INTEGRATION TEST (End-to-End)
# ============================================================================

def test_end_to_end_parsing_and_features():
    """
    End-to-end test: Raw log -> Parse -> Extract Features
    """
    parser = LinuxParser()
    extractor = LinuxFeatureExtractor()

    # Log 1: SSH auth failure
    raw1 = TEST_CASE_1_RAW
    parsed1 = parser.parse(raw1)
    extractor.current_timestamp = datetime(2024, 6, 14, 15, 16, 1)
    features1 = extractor._extract_features(parsed1)

    assert parsed1["event_type"] == "auth_failure"
    assert features1["event_type_code"] == 1
    assert features1["is_new_ip"] == 1.0

    # Log 2: FTP connection from different IP
    raw2 = TEST_CASE_3_RAW
    parsed2 = parser.parse(raw2)
    extractor.current_timestamp = datetime(2024, 6, 17, 7, 7, 0)
    features2 = extractor._extract_features(parsed2)

    assert parsed2["event_type"] == "ftp_connect"
    assert features2["is_new_ip"] == 1.0
    assert features2["event_type_code"] == 6

    # Verify state accumulation
    state = extractor.get_state_summary()
    assert state["unique_ips"] == 2
    assert state["total_events"] == 2
    assert "auth_failure" in state["event_type_counts"]
    assert "ftp_connect" in state["event_type_counts"]


# ============================================================================
# MANUAL TEST CASE SUMMARIES (For Documentation)
# ============================================================================

"""
SUMMARY OF TEST CASES:

Test Case 1 - SSH Auth Failure (Generic IP)
  Raw: "Jun 14 15:16:01 combo sshd(pam_unix)[19939]: authentication failure..."
  Event Type: auth_failure
  Key Features: event_type_code=1, is_new_ip=1.0, ip_failure_streak=1.0
  Anomaly Score: 0.0 (single event)

Test Case 2 - SSH Auth Failure (Root User - Brute Force)
  Raw: "Jun 15 02:04:59 combo sshd(pam_unix)[20882]: authentication failure...user=root"
  Event Type: auth_failure (with user)
  Template ID: E18 (user=root specific template)
  Key Features: is_new_user=1.0, auth_failure_from_new_user=1.0

Test Case 3 - FTP Connection
  Raw: "Jun 17 07:07:00 combo ftpd[29504]: connection from 24.54.76.216..."
  Event Type: ftp_connect
  Data: IP extracted, hostname resolved
  Key Features: event_type_code=6, component_code=4 (ftpd)
  Burst Detection: 0.0 (single connection)
  **With 6+ rapid connections from same IP: anomaly_score += 0.25**

Test Case 4 - Session Management (Open/Close Pair)
  Raw (Open): "Jun 15 04:06:18 combo su(pam_unix)[21416]: session opened for user cyrus..."
  Raw (Close): "Jun 15 04:06:19 combo su(pam_unix)[21416]: session closed for user cyrus"
  Event Types: session_opened, then session_closed
  Key Features: active_session_count (1.0 -> 0.0), session duration tracking
  Duration: ~1 second

Test Case 5 - Logrotate Alert
  Raw: "Jun 15 04:06:20 combo logrotate: ALERT exited abnormally with [1]"
  Event Type: alert
  Exit Code: 1 (abnormal)
  Key Features: Component=logrotate, status=abnormal_exit
  Anomaly Score: 0.0 (scheduled service alerts are expected)

Test Case 6 - SSH Check Pass
  Raw: "Jun 14 15:16:02 combo sshd(pam_unix)[19937]: check pass; user unknown"
  Event Type: auth_check
  Template ID: E27 (specific template for unknown user checks)
  Status: check_pass


KEY FEATURES EXPLANATION:

1. event_type_code (1-19): Numeric encoding for ML models
2. auth_failures_5m / 10m: Failure frequency in time windows
3. ip_failure_streak: Consecutive failures from IP (resets on success)
4. ftp_burst_detected: 6+ connections in 5min window -> anomaly indicator
5. is_new_ip / is_new_user: First occurrence tracking
6. anomaly_score: Composite score (0.0-1.0) based on multiple indicators
   - ip_failure_streak >= 5: +0.2
   - 6+ unique IPs: +0.15
   - FTP burst >= 6 in 5m: +0.25
   - Low user success rate: +0.15
   - High failure frequency (>10 in 10m): +0.25

INTEGRATION WITH PIPELINE:

1. Raw log -> LinuxParser.parse() -> Parsed dict
2. Parsed dict stored in log.metadata["parsed"]
3. LogInternal -> FeatureExtractor.extract() -> Features dict
4. Features stored in log.metadata["features"]
5. Ready for ML anomaly detection models
"""
