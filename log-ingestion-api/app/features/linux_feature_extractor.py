"""
Stateful feature extractor for Linux logs.
Tracks behavioral patterns and temporal features for anomaly detection.
"""

from collections import defaultdict, deque
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import IntEnum


class EventTypeCode(IntEnum):
    """Numeric encoding for event types"""
    AUTH_FAILURE = 1
    AUTH_CHECK = 2
    AUTH_ERROR = 3
    SESSION_OPENED = 4
    SESSION_CLOSED = 5
    FTP_CONNECT = 6
    FTP_TIMEOUT = 7
    FTP_LOGIN = 8
    ALERT = 9
    SERVICE_START = 10
    SERVICE_STOP = 11
    SYSTEM_INFO = 12
    BOOT_EVENT = 13
    SSH_EVENT = 14
    SESSION_EVENT = 15
    FTP_EVENT = 16
    LOGROTATE_EVENT = 17
    GENERIC = 18
    UNKNOWN = 19


class LinuxFeatureExtractor:
    """
    Stateful feature extractor for Linux logs.
    
    Maintains temporal windows and entity tracking for:
    - Authentication failures and checks
    - FTP connections and timeouts
    - Session management
    - IP-based attack indicators
    - User-based anomalies
    """

    # Time windows (in seconds)
    WINDOW_5M = 300
    WINDOW_10M = 600
    WINDOW_1H = 3600

    def __init__(self, max_queue_size: int = 10000):
        """
        Initialize the feature extractor.
        
        Args:
            max_queue_size: Maximum size for event queues (for memory management)
        """
        self.max_queue_size = max_queue_size
        self.current_timestamp = None

        # === Event Type Tracking ===
        self.event_counts = defaultdict(int)  # Total count per event type
        self.event_queue = deque(maxlen=max_queue_size)  # All events with timestamps

        # === IP-based Tracking ===
        self.ip_event_queue = defaultdict(
            lambda: deque(maxlen=max_queue_size)
        )  # Events per IP
        self.ip_first_seen = {}  # Timestamp of first IP occurrence
        self.ip_auth_failures = defaultdict(int)  # Total auth failures per IP
        self.ip_ftp_connections = defaultdict(int)  # Total FTP connections per IP
        self.ip_session_count = defaultdict(int)  # Active sessions per IP

        # === User-based Tracking ===
        self.user_event_queue = defaultdict(
            lambda: deque(maxlen=max_queue_size)
        )  # Events per user
        self.user_first_seen = {}  # Timestamp of first user
        self.user_active_sessions = set()  # Set of users with open sessions
        self.user_auth_failures = defaultdict(int)  # Total failures per user
        self.user_successful_logins = defaultdict(int)  # Total successful sessions

        # === Component-based Tracking ===
        self.component_event_queue = defaultdict(
            lambda: deque(maxlen=max_queue_size)
        )  # Events per component

        # === Session Tracking ===
        self.active_sessions = {}  # {user: timestamp_opened}
        self.session_durations = []  # List of session durations

        # === Failure Streak Tracking ===
        self.ip_failure_streak = defaultdict(int)  # Consecutive failures per IP
        self.ip_last_success_time = {}  # Last successful event per IP

        # === Global Statistics ===
        self.unique_ips_seen = set()
        self.unique_users_seen = set()
        self.total_auth_failures = 0
        self.total_ftp_events = 0

    def extract(self, log_internal: Any) -> Dict[str, Any]:
        """
        Extract features from a LogInternal object.
        
        Interface method that extracts parsed data from metadata and calls extract_features.
        
        Args:
            log_internal: LogInternal object with parsed data in metadata["parsed"]
            
        Returns:
            Dictionary with numeric features for ML models
        """
        # Extract the parsed data from metadata
        parsed_log = log_internal.metadata.get("parsed", {}) if log_internal.metadata else {}
        
        # Update timestamp from log
        if hasattr(log_internal, 'timestamp'):
            self.current_timestamp = log_internal.timestamp
        
        return self._extract_features(parsed_log)

    def _extract_features(self, parsed_log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract features from a parsed log event.
        
        Updates internal state and returns feature vector.
        
        Args:
            parsed_log: Dictionary from LinuxParser.parse()
            
        Returns:
            Dictionary with numeric features for ML models
        """
        # Extract metadata
        event_type = parsed_log.get("event_type", "unknown")
        component = parsed_log.get("component", "unknown")
        user = parsed_log.get("user")
        ip = parsed_log.get("ip")
        status = parsed_log.get("status")
        timestamp = self.current_timestamp or datetime.now()

        # Update current timestamp
        self.current_timestamp = timestamp

        # === Update Global State ===
        self._update_global_state(event_type, parsed_log, timestamp)
        self._update_ip_state(ip, event_type, status, timestamp)
        self._update_user_state(user, event_type, status, timestamp)
        self._update_component_state(component, event_type, timestamp)
        self._update_session_state(user, event_type, timestamp)

        # === Extract Features ===
        features = {
            "event_type_code": self._encode_event_type(event_type),
            "component_code": self._encode_component(component),
        }

        # Time-window features (5min, 10min)
        features.update(self._extract_temporal_features(timestamp))

        # IP-based features
        if ip:
            features.update(self._extract_ip_features(ip, timestamp))

        # User-based features
        if user:
            features.update(self._extract_user_features(user, timestamp))

        # Session-based features
        features.update(self._extract_session_features(timestamp))

        # Event status features
        features.update(self._extract_status_features(
            event_type, status, ip, user
        ))

        # Anomaly indicators
        features.update(self._extract_anomaly_indicators(
            event_type, ip, user, timestamp
        ))

        return features

    # ============================================================================
    # STATE UPDATE METHODS
    # ============================================================================

    def _update_global_state(
        self, event_type: str, parsed_log: Dict[str, Any], timestamp: datetime
    ) -> None:
        """Update global event tracking"""
        self.event_counts[event_type] += 1
        self.event_queue.append((timestamp, event_type, parsed_log))

        # Track auth failures and FTP
        if event_type == "auth_failure":
            self.total_auth_failures += 1
        elif event_type in ["ftp_connect", "ftp_timeout", "ftp_login"]:
            self.total_ftp_events += 1

    def _update_ip_state(
        self, ip: Optional[str], event_type: str, status: Optional[str],
        timestamp: datetime
    ) -> None:
        """Update IP-based state tracking"""
        if not ip:
            return

        # Track first occurrence
        if ip not in self.ip_first_seen:
            self.ip_first_seen[ip] = timestamp
            self.unique_ips_seen.add(ip)

        # Add to IP event queue
        self.ip_event_queue[ip].append((timestamp, event_type))

        # Track auth failures and successes
        if event_type == "auth_failure":
            self.ip_auth_failures[ip] += 1
            self.ip_failure_streak[ip] += 1
        elif event_type in ["session_opened", "ftp_login"]:
            self.ip_failure_streak[ip] = 0  # Reset streak on success
            self.ip_last_success_time[ip] = timestamp

        # Track FTP connections
        if event_type in ["ftp_connect", "ftp_timeout", "ftp_login"]:
            self.ip_ftp_connections[ip] += 1

        # Track sessions
        if event_type == "session_opened":
            self.ip_session_count[ip] += 1
        elif event_type == "session_closed":
            self.ip_session_count[ip] = max(0, self.ip_session_count[ip] - 1)

    def _update_user_state(
        self, user: Optional[str], event_type: str, status: Optional[str],
        timestamp: datetime
    ) -> None:
        """Update user-based state tracking"""
        if not user:
            return

        # Track first occurrence
        if user not in self.user_first_seen:
            self.user_first_seen[user] = timestamp
            self.unique_users_seen.add(user)

        # Add to user event queue
        self.user_event_queue[user].append((timestamp, event_type))

        # Track authentication
        if event_type == "auth_failure":
            self.user_auth_failures[user] += 1
        elif event_type == "session_opened":
            self.user_successful_logins[user] += 1

    def _update_component_state(
        self, component: str, event_type: str, timestamp: datetime
    ) -> None:
        """Update component-based state tracking"""
        if component and component != "unknown":
            self.component_event_queue[component].append((timestamp, event_type))

    def _update_session_state(
        self, user: Optional[str], event_type: str, timestamp: datetime
    ) -> None:
        """Update session state (open/close tracking)"""
        if not user:
            return

        if event_type == "session_opened":
            self.active_sessions[user] = timestamp
            self.user_active_sessions.add(user)
        elif event_type == "session_closed":
            if user in self.active_sessions:
                duration = (
                    timestamp - self.active_sessions[user]
                ).total_seconds()
                self.session_durations.append(duration)
                del self.active_sessions[user]
                self.user_active_sessions.discard(user)

    # ============================================================================
    # FEATURE EXTRACTION METHODS
    # ============================================================================

    def _extract_temporal_features(self, timestamp: datetime) -> Dict[str, float]:
        """Extract time-window based features"""
        features = {}

        # Count events in sliding windows
        window_5m_start = timestamp - timedelta(seconds=self.WINDOW_5M)
        window_10m_start = timestamp - timedelta(seconds=self.WINDOW_10M)
        window_1h_start = timestamp - timedelta(seconds=self.WINDOW_1H)

        auth_failures_5m = 0
        auth_failures_10m = 0
        ftp_events_5m = 0
        ftp_events_10m = 0
        event_count_5m = 0
        event_count_10m = 0

        for ts, event_type, _ in self.event_queue:
            if ts >= window_5m_start:
                event_count_5m += 1
                if event_type == "auth_failure":
                    auth_failures_5m += 1
                elif event_type in ["ftp_connect", "ftp_timeout", "ftp_login"]:
                    ftp_events_5m += 1

            if ts >= window_10m_start:
                event_count_10m += 1
                if event_type == "auth_failure":
                    auth_failures_10m += 1
                elif event_type in ["ftp_connect", "ftp_timeout", "ftp_login"]:
                    ftp_events_10m += 1

        features["auth_failures_5m"] = float(auth_failures_5m)
        features["auth_failures_10m"] = float(auth_failures_10m)
        features["ftp_events_5m"] = float(ftp_events_5m)
        features["ftp_events_10m"] = float(ftp_events_10m)
        features["event_count_5m"] = float(event_count_5m)
        features["event_count_10m"] = float(event_count_10m)

        # Rates
        features["auth_failure_rate_5m"] = (
            auth_failures_5m / event_count_5m if event_count_5m > 0 else 0.0
        )
        features["ftp_event_rate_5m"] = (
            ftp_events_5m / event_count_5m if event_count_5m > 0 else 0.0
        )

        return features

    def _extract_ip_features(self, ip: str, timestamp: datetime) -> Dict[str, float]:
        """Extract IP-based behavioral features"""
        features = {}

        # Time since first seen
        if ip in self.ip_first_seen:
            age_seconds = (timestamp - self.ip_first_seen[ip]).total_seconds()
            features["ip_age_seconds"] = float(age_seconds)
            features["is_new_ip"] = 1.0 if age_seconds < 60 else 0.0
        else:
            features["ip_age_seconds"] = 0.0
            features["is_new_ip"] = 1.0

        # Frequency in time windows
        window_5m_start = timestamp - timedelta(seconds=self.WINDOW_5M)
        window_10m_start = timestamp - timedelta(seconds=self.WINDOW_10M)

        ip_events_5m = sum(
            1 for ts, _ in self.ip_event_queue[ip]
            if ts >= window_5m_start
        )
        ip_events_10m = sum(
            1 for ts, _ in self.ip_event_queue[ip]
            if ts >= window_10m_start
        )

        features["ip_events_5m"] = float(ip_events_5m)
        features["ip_events_10m"] = float(ip_events_10m)

        # Failure metrics
        features["ip_total_auth_failures"] = float(self.ip_auth_failures[ip])
        features["ip_failure_streak"] = float(self.ip_failure_streak[ip])
        features["ip_ftp_connections"] = float(self.ip_ftp_connections[ip])
        features["ip_active_sessions"] = float(self.ip_session_count[ip])

        # Failure rate
        total_ip_events = len(self.ip_event_queue[ip])
        features["ip_failure_rate"] = (
            self.ip_auth_failures[ip] / total_ip_events
            if total_ip_events > 0
            else 0.0
        )

        return features

    def _extract_user_features(self, user: str, timestamp: datetime) -> Dict[str, float]:
        """Extract user-based behavioral features"""
        features = {}

        # Time since first seen
        if user in self.user_first_seen:
            age_seconds = (timestamp - self.user_first_seen[user]).total_seconds()
            features["user_age_seconds"] = float(age_seconds)
            features["is_new_user"] = 1.0 if age_seconds < 60 else 0.0
        else:
            features["user_age_seconds"] = 0.0
            features["is_new_user"] = 1.0

        # Frequency in time windows
        window_5m_start = timestamp - timedelta(seconds=self.WINDOW_5M)
        window_10m_start = timestamp - timedelta(seconds=self.WINDOW_10M)

        user_events_5m = sum(
            1 for ts, _ in self.user_event_queue[user]
            if ts >= window_5m_start
        )
        user_events_10m = sum(
            1 for ts, _ in self.user_event_queue[user]
            if ts >= window_10m_start
        )

        features["user_events_5m"] = float(user_events_5m)
        features["user_events_10m"] = float(user_events_10m)

        # Auth metrics
        features["user_auth_failures"] = float(self.user_auth_failures[user])
        features["user_successful_logins"] = float(self.user_successful_logins[user])

        # Login success rate
        total_user_auth_attempts = (
            self.user_auth_failures[user] + self.user_successful_logins[user]
        )
        features["user_success_rate"] = (
            self.user_successful_logins[user] / total_user_auth_attempts
            if total_user_auth_attempts > 0
            else 0.0
        )

        return features

    def _extract_session_features(self, timestamp: datetime) -> Dict[str, float]:
        """Extract session-based features"""
        features = {}

        # Current active sessions
        features["active_session_count"] = float(len(self.active_sessions))
        features["unique_users_with_sessions"] = float(
            len(self.user_active_sessions)
        )

        # Session duration statistics
        if self.session_durations:
            avg_session_duration = sum(self.session_durations) / len(
                self.session_durations
            )
            max_session_duration = max(self.session_durations)
            features["avg_session_duration"] = float(avg_session_duration)
            features["max_session_duration"] = float(max_session_duration)
        else:
            features["avg_session_duration"] = 0.0
            features["max_session_duration"] = 0.0

        return features

    def _extract_status_features(
        self, event_type: str, status: Optional[str], ip: Optional[str],
        user: Optional[str]
    ) -> Dict[str, float]:
        """Extract status-based features"""
        features = {}

        # Event type specific status
        if event_type == "auth_failure":
            features["is_auth_failure"] = 1.0
            features["auth_failure_from_new_ip"] = (
                1.0 if ip and ip not in self.ip_first_seen else 0.0
            )
            features["auth_failure_from_new_user"] = (
                1.0 if user and user not in self.user_first_seen else 0.0
            )
        else:
            features["is_auth_failure"] = 0.0
            features["auth_failure_from_new_ip"] = 0.0
            features["auth_failure_from_new_user"] = 0.0

        if event_type == "ftp_timeout":
            features["is_ftp_timeout"] = 1.0
        else:
            features["is_ftp_timeout"] = 0.0

        if event_type == "session_opened":
            features["is_session_open"] = 1.0
        elif event_type == "session_closed":
            features["is_session_close"] = 1.0
        else:
            features["is_session_open"] = 0.0
            features["is_session_close"] = 0.0

        return features

    def _extract_anomaly_indicators(
        self, event_type: str, ip: Optional[str], user: Optional[str],
        timestamp: datetime
    ) -> Dict[str, float]:
        """Extract anomaly score indicators"""
        features = {}

        anomaly_score = 0.0

        # Indicator 1: High failure streak from IP
        if ip and self.ip_failure_streak[ip] >= 5:
            anomaly_score += 0.2
            features["ip_high_failure_streak"] = 1.0
        else:
            features["ip_high_failure_streak"] = 0.0

        # Indicator 2: Multiple new IPs in short time
        if len(self.unique_ips_seen) > 10:
            features["multiple_new_ips"] = 1.0
            anomaly_score += 0.15
        else:
            features["multiple_new_ips"] = 0.0

        # Indicator 3: Burst of FTP connections
        if ip:
            window_5m_start = timestamp - timedelta(seconds=self.WINDOW_5M)
            ftp_burst = sum(
                1 for ts, et in self.ip_event_queue[ip]
                if ts >= window_5m_start and et in ["ftp_connect", "ftp_timeout", "ftp_login"]
            )
            if ftp_burst > 5:
                features["ftp_burst_detected"] = 1.0
                anomaly_score += 0.25
            else:
                features["ftp_burst_detected"] = 0.0
        else:
            features["ftp_burst_detected"] = 0.0

        # Indicator 4: Low user success rate
        if user and self.user_auth_failures[user] > 2:
            total = self.user_auth_failures[user] + self.user_successful_logins[user]
            success_rate = self.user_successful_logins[user] / total if total > 0 else 0
            if success_rate < 0.2:
                features["user_low_success_rate"] = 1.0
                anomaly_score += 0.15
            else:
                features["user_low_success_rate"] = 0.0
        else:
            features["user_low_success_rate"] = 0.0

        # Indicator 5: High frequency of failures
        window_10m_start = timestamp - timedelta(seconds=self.WINDOW_10M)
        recent_failures = sum(
            1 for ts, et, _ in self.event_queue
            if ts >= window_10m_start and et == "auth_failure"
        )
        if recent_failures > 10:
            features["high_failure_frequency"] = 1.0
            anomaly_score += 0.25
        else:
            features["high_failure_frequency"] = 0.0

        features["anomaly_score"] = min(anomaly_score, 1.0)

        return features

    # ============================================================================
    # UTILITY ENCODING METHODS
    # ============================================================================

    def _encode_event_type(self, event_type: str) -> int:
        """Map event type string to integer code"""
        mapping = {
            "auth_failure": EventTypeCode.AUTH_FAILURE,
            "auth_check": EventTypeCode.AUTH_CHECK,
            "auth_error": EventTypeCode.AUTH_ERROR,
            "session_opened": EventTypeCode.SESSION_OPENED,
            "session_closed": EventTypeCode.SESSION_CLOSED,
            "ftp_connect": EventTypeCode.FTP_CONNECT,
            "ftp_timeout": EventTypeCode.FTP_TIMEOUT,
            "ftp_login": EventTypeCode.FTP_LOGIN,
            "alert": EventTypeCode.ALERT,
            "service_start": EventTypeCode.SERVICE_START,
            "service_stop": EventTypeCode.SERVICE_STOP,
            "system_info": EventTypeCode.SYSTEM_INFO,
            "boot_event": EventTypeCode.BOOT_EVENT,
            "ssh_event": EventTypeCode.SSH_EVENT,
            "session_event": EventTypeCode.SESSION_EVENT,
            "ftp_event": EventTypeCode.FTP_EVENT,
            "logrotate_event": EventTypeCode.LOGROTATE_EVENT,
            "generic": EventTypeCode.GENERIC,
            "unknown": EventTypeCode.UNKNOWN,
        }
        return int(mapping.get(event_type, EventTypeCode.UNKNOWN))

    def _encode_component(self, component: str) -> int:
        """Map component string to integer code"""
        mapping = {
            "sshd": 1,
            "su": 2,
            "login": 3,
            "ftpd": 4,
            "logrotate": 5,
            "kernel": 6,
            "unknown": 0,
        }
        return mapping.get(component, 0)

    # ============================================================================
    # STATE INSPECTION (DEBUGGING)
    # ============================================================================

    def get_state_summary(self) -> Dict[str, Any]:
        """Return summary of current internal state (for debugging)"""
        return {
            "total_events": len(self.event_queue),
            "unique_ips": len(self.unique_ips_seen),
            "unique_users": len(self.unique_users_seen),
            "active_sessions": len(self.active_sessions),
            "total_auth_failures": self.total_auth_failures,
            "total_ftp_events": self.total_ftp_events,
            "event_type_counts": dict(self.event_counts),
        }
