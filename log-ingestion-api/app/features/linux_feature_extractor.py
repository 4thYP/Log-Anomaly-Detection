"""
STEP 4: Stateful feature extractor for Linux logs.
Tracks per-server behavioral patterns with fixed 14-element feature vectors.
"""

from collections import defaultdict, deque
from typing import Dict, Any, Optional, List
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


class LinuxServerState:
    """Per-server state for Linux feature extraction (STEP 4)"""
    
    def __init__(self, max_queue_size: int = 1000):
        """Initialize per-server state tracking"""
        # Event frequency tracking
        self.event_timestamp_queue: deque = deque(maxlen=max_queue_size)
        self.event_type_counts: Dict[str, int] = defaultdict(int)
        
        # IP tracking
        self.ip_last_seen: Dict[str, datetime] = {}
        self.ip_failure_counts: Dict[str, int] = defaultdict(int)
        self.ip_failure_streaks: Dict[str, int] = defaultdict(int)
        self.ip_first_seen: Dict[str, datetime] = {}
        self.ip_total_events: Dict[str, int] = defaultdict(int)
        self.ip_ftp_connections: Dict[str, int] = defaultdict(int)
        self.ip_event_queue: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_queue_size))
        
        # User tracking
        self.user_first_seen: Dict[str, datetime] = {}
        self.user_event_counts: Dict[str, int] = defaultdict(int)
        self.user_failure_counts: Dict[str, int] = defaultdict(int)
        self.user_success_counts: Dict[str, int] = defaultdict(int)
        
        # Session tracking
        self.active_sessions: Dict[str, datetime] = {}
        self.session_durations: List[float] = []
        
        # Component tracking
        self.component_event_counts: Dict[str, int] = defaultdict(int)
        self.component_error_counts: Dict[str, int] = defaultdict(int)
        
        # Temporal state
        self.last_event_time: Optional[datetime] = None
        self.event_intervals: deque = deque(maxlen=100)
        
        # Global counts for this server
        self.total_events_seen: int = 0
        self.total_auth_failures: int = 0
        self.total_ftp_events: int = 0


class LinuxFeatureExtractor:
    """
    Stateful feature extractor for Linux logs (STEP 4 design).
    
    Per-server state isolation:
    - Maintains separate state for each server (sid)
    - Uses log_internal.timestamp (not datetime.now())
    - Returns fixed 14-element feature vector
    - All features normalized to [0, 1]
    """

    # Time windows (in seconds)
    WINDOW_5M = 300
    WINDOW_10M = 600
    WINDOW_1H = 3600
    
    # Normalization constants
    MAX_EVENT_TYPE = 19  # EventTypeCode.UNKNOWN
    MAX_TEMPLATE_ID = 50
    MAX_IPS_IN_WINDOW = 100
    MAX_FAILURE_STREAK = 20
    MAX_FTP_BURST = 20
    MAX_COMPONENT_ANOMALY = 10

    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize the feature extractor.
        
        Args:
            max_queue_size: Maximum size for per-server event queues
        """
        self.max_queue_size = max_queue_size
        # Per-server state storage: sid -> LinuxServerState
        self.server_states: Dict[str, LinuxServerState] = {}

    def _get_or_create_server_state(self, sid: str) -> LinuxServerState:
        """Get or create state for a specific server"""
        if sid not in self.server_states:
            self.server_states[sid] = LinuxServerState(self.max_queue_size)
        return self.server_states[sid]

    def extract(self, log_internal: Any) -> List[float]:
        """
        Extract 14-element feature vector from a LogInternal object.
        
        STEP 4 Interface:
        - Uses log_internal.sid for per-server state
        - Uses log_internal.timestamp (NOT datetime.now())
        - Returns List[float] with exactly 14 normalized values
        
        Args:
            log_internal: LogInternal object with parsed data in metadata["parsed"]
            
        Returns:
            List of 14 floats, each in [0, 1] range
        """
        # Extract parsed data from metadata
        parsed_log = (
            log_internal.metadata.get("parsed", {}) 
            if log_internal.metadata 
            else {}
        )
        
        # Get per-server state
        state = self._get_or_create_server_state(log_internal.sid)
        
        # Use log timestamp (NOT datetime.now())
        log_time = log_internal.timestamp
        
        # Update server state with current event
        self._update_server_state(parsed_log, state, log_time)
        
        # Compute 14-element feature vector
        features = self._compute_feature_vector(parsed_log, state, log_time)
        
        # Verify constraints
        assert len(features) == 14, f"Expected 14 features, got {len(features)}"
        assert all(isinstance(f, (int, float)) for f in features), "All features must be numeric"
        assert all(0 <= f <= 1 for f in features), f"All features must be in [0, 1], got {features}"
        
        return features

    def _update_server_state(
        self,
        parsed_log: Dict[str, Any],
        state: LinuxServerState,
        log_time: datetime
    ) -> None:
        """
        Update per-server state with current event.
        
        Args:
            parsed_log: Dictionary with keys event_type, ip, user, component, status
            state: LinuxServerState for this server
            log_time: Timestamp from log (NOT datetime.now())
        """
        event_type = parsed_log.get("event_type", "unknown")
        ip = parsed_log.get("ip")
        user = parsed_log.get("user")
        component = parsed_log.get("component", "unknown")
        status = parsed_log.get("status")
        
        # Update global counts
        state.total_events_seen += 1
        state.event_type_counts[event_type] += 1
        state.event_timestamp_queue.append(log_time)
        state.last_event_time = log_time
        
        # Track auth failures and FTP events
        if event_type == "auth_failure":
            state.total_auth_failures += 1
        elif event_type in ["ftp_connect", "ftp_timeout", "ftp_login"]:
            state.total_ftp_events += 1
        
        # Update IP state
        if ip:
            if ip not in state.ip_first_seen:
                state.ip_first_seen[ip] = log_time
            state.ip_last_seen[ip] = log_time
            state.ip_total_events[ip] += 1
            state.ip_event_queue[ip].append((log_time, event_type))
            
            if event_type == "auth_failure":
                state.ip_failure_counts[ip] += 1
                state.ip_failure_streaks[ip] += 1
            elif event_type in ["session_opened", "ftp_login"]:
                state.ip_failure_streaks[ip] = 0  # Reset streak on success
            
            if event_type in ["ftp_connect", "ftp_timeout", "ftp_login"]:
                state.ip_ftp_connections[ip] += 1
        
        # Update user state
        if user:
            if user not in state.user_first_seen:
                state.user_first_seen[user] = log_time
            state.user_event_counts[user] += 1
            
            if event_type == "auth_failure":
                state.user_failure_counts[user] += 1
            elif event_type in ["session_opened", "ftp_login"]:
                state.user_success_counts[user] += 1
        
        # Update session state
        if user:
            if event_type == "session_opened":
                state.active_sessions[user] = log_time
            elif event_type == "session_closed" and user in state.active_sessions:
                duration = (log_time - state.active_sessions[user]).total_seconds()
                state.session_durations.append(duration)
                del state.active_sessions[user]
        
        # Update component state
        if component and component != "unknown":
            state.component_event_counts[component] += 1
            if event_type in ["auth_failure", "alert", "error"]:
                state.component_error_counts[component] += 1
        
        # Update temporal intervals
        if state.last_event_time and len(state.event_timestamp_queue) > 1:
            prev_time = state.event_timestamp_queue[-2] if len(state.event_timestamp_queue) > 1 else None
            if prev_time:
                interval = (log_time - prev_time).total_seconds()
                if interval > 0:
                    state.event_intervals.append(interval)

    def _compute_feature_vector(
        self,
        parsed_log: Dict[str, Any],
        state: LinuxServerState,
        log_time: datetime
    ) -> List[float]:
        """
        Compute 14-element normalized feature vector.
        
        FEATURE ORDER (must match specification):
        0. event_type_code
        1. template_id_normalized
        2. auth_failure_rate_5m
        3. unique_ips_5m
        4. ip_failure_streak
        5. ftp_connection_burst
        6. session_anomaly_score
        7. error_event_density
        8. is_auth_failure_flag
        9. is_new_ip_flag
        10. auth_burst_detected
        11. component_anomaly
        12. temporal_entropy
        13. overall_anomaly_score
        """
        event_type = parsed_log.get("event_type", "unknown")
        ip = parsed_log.get("ip")
        user = parsed_log.get("user")
        component = parsed_log.get("component", "unknown")
        status = parsed_log.get("status")
        template_id = parsed_log.get("template_id", 0)
        
        features = []
        
        # Feature 0: event_type_code (1-19, normalized to 0-1)
        event_code = self._encode_event_type(event_type)
        feature_0 = float(event_code) / self.MAX_EVENT_TYPE
        features.append(min(feature_0, 1.0))
        
        # Feature 1: template_id_normalized (0-1)
        feature_1 = min(float(template_id), self.MAX_TEMPLATE_ID) / self.MAX_TEMPLATE_ID
        features.append(feature_1)
        
        # Feature 2: auth_failure_rate_5m (0-1)
        feature_2 = self._compute_auth_failure_rate_5m(state, log_time)
        features.append(feature_2)
        
        # Feature 3: unique_ips_5m (0-1, normalized count)
        feature_3 = self._compute_unique_ips_5m(state, log_time)
        features.append(feature_3)
        
        # Feature 4: ip_failure_streak (0-1)
        feature_4 = self._compute_ip_failure_streak(ip, state)
        features.append(feature_4)
        
        # Feature 5: ftp_connection_burst (0-1)
        feature_5 = self._compute_ftp_burst(ip, state, log_time)
        features.append(feature_5)
        
        # Feature 6: session_anomaly_score (0-1)
        feature_6 = self._compute_session_anomaly(state, log_time)
        features.append(feature_6)
        
        # Feature 7: error_event_density (0-1)
        feature_7 = self._compute_error_density_5m(state, log_time)
        features.append(feature_7)
        
        # Feature 8: is_auth_failure_flag (0 or 1)
        feature_8 = 1.0 if event_type == "auth_failure" else 0.0
        features.append(feature_8)
        
        # Feature 9: is_new_ip_flag (0 or 1)
        feature_9 = self._compute_is_new_ip(ip, state, log_time)
        features.append(feature_9)
        
        # Feature 10: auth_burst_detected (0-1)
        feature_10 = self._compute_auth_burst(state, log_time)
        features.append(feature_10)
        
        # Feature 11: component_anomaly (0-1)
        feature_11 = self._compute_component_anomaly(component, state)
        features.append(feature_11)
        
        # Feature 12: temporal_entropy (0-1)
        feature_12 = self._compute_temporal_entropy(state)
        features.append(feature_12)
        
        # Feature 13: overall_anomaly_score (0-1)
        feature_13 = self._compute_overall_anomaly_score(features)
        features.append(feature_13)
        
        return features

    # ============================================================================
    # FEATURE COMPUTATION METHODS
    # ============================================================================

    def _compute_auth_failure_rate_5m(self, state: LinuxServerState, log_time: datetime) -> float:
        """Compute auth failure rate in 5-minute window"""
        window_start = log_time - timedelta(seconds=self.WINDOW_5M)
        
        # Count total events and auth failures in window
        total_events_5m = sum(1 for ts in state.event_timestamp_queue if ts >= window_start)
        if total_events_5m == 0:
            return 0.0
        
        # Count auth failures (approximate using stored count)
        auth_failures_5m = state.event_type_counts.get("auth_failure", 0)
        rate = min(float(auth_failures_5m) / total_events_5m, 1.0)
        return rate

    def _compute_unique_ips_5m(self, state: LinuxServerState, log_time: datetime) -> float:
        """Compute normalized count of unique IPs in 5-minute window"""
        window_start = log_time - timedelta(seconds=self.WINDOW_5M)
        
        unique_ips = set()
        for ip, events_queue in state.ip_event_queue.items():
            for ts, _ in events_queue:
                if ts >= window_start:
                    unique_ips.add(ip)
                    break
        
        count = len(unique_ips)
        normalized = min(float(count) / self.MAX_IPS_IN_WINDOW, 1.0)
        return normalized

    def _compute_ip_failure_streak(self, ip: Optional[str], state: LinuxServerState) -> float:
        """Compute normalized IP failure streak"""
        if not ip or ip not in state.ip_failure_streaks:
            return 0.0
        
        streak = state.ip_failure_streaks[ip]
        normalized = min(float(streak) / self.MAX_FAILURE_STREAK, 1.0)
        return normalized

    def _compute_ftp_burst(self, ip: Optional[str], state: LinuxServerState, log_time: datetime) -> float:
        """Compute FTP connection burst indicator (rapid connections)"""
        if not ip:
            return 0.0
        
        window_start = log_time - timedelta(seconds=self.WINDOW_5M)
        
        ftp_count = sum(
            1 for ts, et in state.ip_event_queue[ip]
            if ts >= window_start and et in ["ftp_connect", "ftp_timeout", "ftp_login"]
        )
        
        normalized = min(float(ftp_count) / self.MAX_FTP_BURST, 1.0)
        return normalized

    def _compute_session_anomaly(self, state: LinuxServerState, log_time: datetime) -> float:
        """Compute session anomaly score"""
        if not state.session_durations:
            return 0.0
        
        avg_duration = sum(state.session_durations) / len(state.session_durations)
        
        # Anomaly if unusually short or long
        if avg_duration < 10:  # Very short session
            return 1.0
        elif avg_duration > 7200:  # Very long session (> 2 hours)
            return 0.5
        else:
            return 0.0

    def _compute_error_density_5m(self, state: LinuxServerState, log_time: datetime) -> float:
        """Compute error event density in 5-minute window"""
        window_start = log_time - timedelta(seconds=self.WINDOW_5M)
        
        total_events_5m = sum(1 for ts in state.event_timestamp_queue if ts >= window_start)
        error_events = (
            state.event_type_counts.get("auth_failure", 0) +
            state.event_type_counts.get("alert", 0)
        )
        
        if total_events_5m == 0:
            return 0.0
        
        density = min(float(error_events) / total_events_5m, 1.0)
        return density

    def _compute_is_new_ip(self, ip: Optional[str], state: LinuxServerState, log_time: datetime) -> float:
        """Check if IP is newly seen"""
        if not ip:
            return 0.0
        
        if ip not in state.ip_first_seen:
            return 1.0
        
        age_seconds = (log_time - state.ip_first_seen[ip]).total_seconds()
        return 1.0 if age_seconds < 60 else 0.0

    def _compute_auth_burst(self, state: LinuxServerState, log_time: datetime) -> float:
        """Compute auth failure burst detection"""
        # Detect burst: more than 3 failures total
        if state.total_auth_failures > 3:
            burst = min(float(state.total_auth_failures) / 10.0, 1.0)
            return burst
        
        return 0.0

    def _compute_component_anomaly(self, component: str, state: LinuxServerState) -> float:
        """Compute component-level anomaly score"""
        if not component or component == "unknown":
            return 0.0
        
        total_component_events = state.component_event_counts.get(component, 0)
        error_events = state.component_error_counts.get(component, 0)
        
        if total_component_events == 0:
            return 0.0
        
        error_rate = float(error_events) / total_component_events
        normalized = min(error_rate * 2, 1.0)  # Scale up sensitivity
        return normalized

    def _compute_temporal_entropy(self, state: LinuxServerState) -> float:
        """Compute temporal entropy (randomness/chaos of event intervals)"""
        if not state.event_intervals or len(state.event_intervals) < 2:
            return 0.0
        
        # Calculate coefficient of variation
        intervals = list(state.event_intervals)
        mean_interval = sum(intervals) / len(intervals)
        
        if mean_interval == 0:
            return 0.0
        
        variance = sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)
        std_dev = variance ** 0.5
        cv = std_dev / mean_interval if mean_interval > 0 else 0.0
        
        # Normalize: entropy = min(cv, 2.0) / 2.0
        entropy = min(cv / 2.0, 1.0)
        return entropy

    def _compute_overall_anomaly_score(self, features: List[float]) -> float:
        """
        Compute overall anomaly score from first 13 features.
        
        Weighted sum based on importance:
        - auth failures (high)
        - IP reputation/failure metrics (high)
        - temporal anomalies (medium)
        - component/session metrics (low)
        """
        if len(features) < 13:
            return 0.0
        
        # Weighted sum of features 0-12
        weights = [
            0.05,  # 0: event_type_code
            0.02,  # 1: template_id_normalized
            0.15,  # 2: auth_failure_rate_5m
            0.10,  # 3: unique_ips_5m
            0.15,  # 4: ip_failure_streak
            0.12,  # 5: ftp_connection_burst
            0.08,  # 6: session_anomaly_score
            0.12,  # 7: error_event_density
            0.10,  # 8: is_auth_failure_flag
            0.08,  # 9: is_new_ip_flag
            0.12,  # 10: auth_burst_detected
            0.08,  # 11: component_anomaly
            0.06,  # 12: temporal_entropy
        ]
        
        score = sum(f * w for f, w in zip(features[:13], weights))
        return min(score, 1.0)

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
