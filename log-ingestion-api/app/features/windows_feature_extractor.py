"""
STEP 4: Stateful feature extractor for Windows event logs.
Tracks per-server behavioral patterns with fixed 12-element feature vectors.
"""

from collections import defaultdict, deque
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from enum import IntEnum

from app.models.log_models import LogInternal


class WindowsEventTypeCode(IntEnum):
    """Numeric encoding for Windows event types"""
    SERVICE_START = 1
    SERVICE_STOP = 2
    TRANSACTION_CREATE = 3
    TRANSACTION_CLOSE = 4
    PACKAGE_APPLICABILITY = 5
    PACKAGE_ERROR = 6
    SESSION_INITIALIZED = 7
    SESSION_DESTROYED = 8
    MANIFEST_ERROR = 9
    PARSE_ERROR = 10
    UPLOAD_ERROR = 11
    CRYPT_ERROR = 12
    REGISTRY_ERROR = 13
    FILE_ERROR = 14
    HRESULT_ERROR = 15
    UNKNOWN = 16


class WindowsServerState:
    """Per-server state for Windows feature extraction (STEP 4)"""
    
    def __init__(self, max_queue_size: int = 1000):
        """Initialize per-server state tracking"""
        # Event frequency tracking
        self.event_timestamp_queue: deque = deque(maxlen=max_queue_size)
        self.event_type_counts: Dict[str, int] = defaultdict(int)
        
        # Error tracking
        self.error_codes: deque = deque(maxlen=100)
        self.error_hresults: Dict[str, int] = defaultdict(int)
        self.error_names: Dict[str, int] = defaultdict(int)
        self.consecutive_errors: int = 0
        self.max_consecutive_errors: int = 0
        
        # Event-level counts
        self.total_events: int = 0
        self.total_errors: int = 0
        self.total_failures: int = 0
        
        # Transaction tracking
        self.active_transactions: Dict[str, datetime] = {}
        self.transaction_handles: deque = deque(maxlen=50)
        self.transaction_success_count: int = 0
        self.transaction_failure_count: int = 0
        
        # Package tracking
        self.packages_seen: set = set()
        self.package_errors: Dict[str, int] = defaultdict(int)
        
        # Session tracking
        self.active_sessions: set = set()
        self.session_events: Dict[str, int] = defaultdict(int)
        
        # Service state tracking
        self.service_state: str = "unknown"
        self.service_startup_time: Optional[datetime] = None
        self.service_state_transitions: int = 0
        
        # Component tracking
        self.component_counts: Dict[str, int] = defaultdict(int)
        self.component_error_counts: Dict[str, int] = defaultdict(int)
        
        # Temporal state
        self.last_event_time: Optional[datetime] = None


class WindowsFeatureExtractor:
    """
    Stateful feature extractor for Windows event logs (STEP 4 design).
    
    Per-server state isolation:
    - Maintains separate state for each server (sid)
    - Uses log_internal.timestamp (not datetime.now())
    - Returns fixed 12-element feature vector
    - All features normalized to [0, 1]
    """
    
    # Time windows (in seconds)
    WINDOW_5M = 300
    WINDOW_10M = 600
    WINDOW_1H = 3600
    
    # Normalization constants
    MAX_EVENT_TYPE = 16  # WindowsEventTypeCode.UNKNOWN
    MAX_TEMPLATE_ID = 100
    MAX_HRESULT_BUCKET = 10
    MAX_CONSECUTIVE_ERRORS = 20
    
    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize the feature extractor.
        
        Args:
            max_queue_size: Maximum size for per-server event queues
        """
        self.max_queue_size = max_queue_size
        # Per-server state storage: sid -> WindowsServerState
        self.server_states: Dict[str, WindowsServerState] = {}
    
    def _get_or_create_server_state(self, sid: str) -> WindowsServerState:
        """Get or create state for a specific server"""
        if sid not in self.server_states:
            self.server_states[sid] = WindowsServerState(self.max_queue_size)
        return self.server_states[sid]

    def extract(self, log_internal: LogInternal) -> List[float]:
        """
        Extract 12-element feature vector from a LogInternal object.
        
        STEP 4 Interface:
        - Uses log_internal.sid for per-server state
        - Uses log_internal.timestamp (NOT datetime.now())
        - Returns List[float] with exactly 12 normalized values
        
        Args:
            log_internal: LogInternal object with parsed data in metadata["parsed"]
            
        Returns:
            List of 12 floats, each in [0, 1] range
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
        
        # Compute 12-element feature vector
        features = self._compute_feature_vector(parsed_log, state, log_time)
        
        # Verify constraints
        assert len(features) == 12, f"Expected 12 features, got {len(features)}"
        assert all(isinstance(f, (int, float)) for f in features), "All features must be numeric"
        assert all(0 <= f <= 1 for f in features), f"All features must be in [0, 1], got {features}"
        
        return features

    
    # ============================================================================
    # STATE UPDATE
    # ============================================================================
    
    def _update_server_state(
        self,
        parsed_log: Dict[str, Any],
        state: WindowsServerState,
        log_time: datetime
    ) -> None:
        """
        Update per-server state with current event.
        
        Args:
            parsed_log: Dictionary with event data
            state: WindowsServerState for this server
            log_time: Timestamp from log (NOT datetime.now())
        """
        state.total_events += 1
        
        event_type = parsed_log.get("event_type", "unknown")
        component = parsed_log.get("component", "unknown")
        status = parsed_log.get("status", "info")
        
        # Update counters
        state.event_type_counts[event_type] += 1
        state.component_counts[component] += 1
        state.event_timestamp_queue.append(log_time)
        state.last_event_time = log_time
        
        # Update error tracking
        if status in ["failure", "error", "warning"]:
            state.total_errors += 1
            state.consecutive_errors += 1
            state.max_consecutive_errors = max(
                state.max_consecutive_errors, state.consecutive_errors
            )
            
            hresult = parsed_log.get("hresult")
            error_name = parsed_log.get("error_name")
            if hresult:
                state.error_hresults[hresult] += 1
            if error_name:
                state.error_names[error_name] += 1
                state.error_codes.append(error_name)
            
            if status == "failure":
                state.total_failures += 1
            
            if component and component != "unknown":
                state.component_error_counts[component] += 1
        else:
            state.consecutive_errors = 0
        
        # Update transaction tracking
        if event_type == "transaction_create":
            handle = parsed_log.get("handle")
            if handle:
                state.active_transactions[handle] = log_time
                state.transaction_handles.append(handle)
                if status == "success":
                    state.transaction_success_count += 1
                else:
                    state.transaction_failure_count += 1
        
        # Update package tracking
        if "package" in event_type:
            pkg_name = parsed_log.get("package_name", "unknown")
            state.packages_seen.add(pkg_name)
            if status in ["failure", "error"]:
                state.package_errors[pkg_name] += 1
        
        # Update session tracking
        if "session" in event_type:
            session_id = parsed_log.get("session_id", "unknown")
            if "initialized" in event_type:
                state.active_sessions.add(session_id)
            elif "destroyed" in event_type:
                state.active_sessions.discard(session_id)
            state.session_events[session_id] += 1
        
        # Update service state
        if event_type == "service_start":
            state.service_state = "running"
            state.service_startup_time = log_time
            state.service_state_transitions += 1
        elif event_type == "service_stop":
            state.service_state = "stopped"
            state.service_state_transitions += 1
        elif event_type == "service_init":
            state.service_state = "initializing"

    
    # ============================================================================
    # FEATURE COMPUTATION
    # ============================================================================
    
    def _compute_feature_vector(
        self,
        parsed_log: Dict[str, Any],
        state: WindowsServerState,
        log_time: datetime
    ) -> List[float]:
        """
        Compute 12-element normalized feature vector.
        
        FEATURE ORDER (must match specification):
        0. event_type_code (1-16, normalized to 0-1)
        1. template_id_normalized (0-1)
        2. error_rate_5m (0-1)
        3. transaction_failure_rate (0-1)
        4. error_cascade_indicator (0-1)
        5. hresult_code_bucket (0-1)
        6. service_health_transition (0-1)
        7. package_install_failure_rate (0-1)
        8. is_error_flag (0 or 1)
        9. consecutive_errors_normalized (0-1)
        10. temporal_irregularity (0-1)
        11. overall_anomaly_score (0-1)
        """
        event_type = parsed_log.get("event_type", "unknown")
        component = parsed_log.get("component", "unknown")
        status = parsed_log.get("status", "info")
        template_id = parsed_log.get("template_id", 0)
        
        features = []
        
        # Feature 0: event_type_code (1-16, normalized to 0-1)
        event_code = self._encode_event_type(event_type)
        feature_0 = float(event_code) / self.MAX_EVENT_TYPE
        features.append(min(feature_0, 1.0))
        
        # Feature 1: template_id_normalized (0-1)
        feature_1 = min(float(template_id), self.MAX_TEMPLATE_ID) / self.MAX_TEMPLATE_ID
        features.append(feature_1)
        
        # Feature 2: error_rate_5m (0-1)
        feature_2 = self._compute_error_rate_5m(state, log_time)
        features.append(feature_2)
        
        # Feature 3: transaction_failure_rate (0-1)
        feature_3 = self._compute_transaction_failure_rate(state)
        features.append(feature_3)
        
        # Feature 4: error_cascade_indicator (0-1)
        feature_4 = self._compute_error_cascade(state)
        features.append(feature_4)
        
        # Feature 5: hresult_code_bucket (0-1)
        feature_5 = self._compute_hresult_bucket(state)
        features.append(feature_5)
        
        # Feature 6: service_health_transition (0-1)
        feature_6 = self._compute_service_health_transition(state)
        features.append(feature_6)
        
        # Feature 7: package_install_failure_rate (0-1)
        feature_7 = self._compute_package_failure_rate(state)
        features.append(feature_7)
        
        # Feature 8: is_error_flag (0 or 1)
        feature_8 = 1.0 if status in ["failure", "error", "warning"] else 0.0
        features.append(feature_8)
        
        # Feature 9: consecutive_errors_normalized (0-1)
        feature_9 = self._compute_consecutive_errors_normalized(state)
        features.append(feature_9)
        
        # Feature 10: temporal_irregularity (0-1)
        feature_10 = self._compute_temporal_irregularity(state, log_time)
        features.append(feature_10)
        
        # Feature 11: overall_anomaly_score (0-1)
        feature_11 = self._compute_overall_anomaly_score(features)
        features.append(feature_11)
        
        return features
    
    # ============================================================================
    # HELPER COMPUTATION METHODS
    # ============================================================================
    
    def _encode_event_type(self, event_type: str) -> int:
        """Encode event type string to numeric code"""
        mapping = {
            "service_start": WindowsEventTypeCode.SERVICE_START,
            "service_stop": WindowsEventTypeCode.SERVICE_STOP,
            "transaction_create": WindowsEventTypeCode.TRANSACTION_CREATE,
            "transaction_close": WindowsEventTypeCode.TRANSACTION_CLOSE,
            "package_applicability": WindowsEventTypeCode.PACKAGE_APPLICABILITY,
            "package_error": WindowsEventTypeCode.PACKAGE_ERROR,
            "session_initialized": WindowsEventTypeCode.SESSION_INITIALIZED,
            "session_destroyed": WindowsEventTypeCode.SESSION_DESTROYED,
            "manifest_error": WindowsEventTypeCode.MANIFEST_ERROR,
            "parse_error": WindowsEventTypeCode.PARSE_ERROR,
            "upload_error": WindowsEventTypeCode.UPLOAD_ERROR,
            "crypt_error": WindowsEventTypeCode.CRYPT_ERROR,
            "registry_error": WindowsEventTypeCode.REGISTRY_ERROR,
            "file_error": WindowsEventTypeCode.FILE_ERROR,
            "hresult_error": WindowsEventTypeCode.HRESULT_ERROR,
        }
        return mapping.get(event_type, WindowsEventTypeCode.UNKNOWN)
    
    def _compute_error_rate_5m(self, state: WindowsServerState, log_time: datetime) -> float:
        """Compute error rate in 5-minute window"""
        window_start = log_time - timedelta(seconds=self.WINDOW_5M)
        
        # Count total events in window
        total_events_5m = sum(1 for ts in state.event_timestamp_queue if ts >= window_start)
        if total_events_5m == 0:
            return 0.0
        
        # Count errors in window (approximate using total error count)
        error_count = state.total_errors
        rate = min(float(error_count) / (total_events_5m + 1), 1.0)
        return rate
    
    def _compute_transaction_failure_rate(self, state: WindowsServerState) -> float:
        """Compute transaction failure rate"""
        total_transactions = (
            state.transaction_success_count + state.transaction_failure_count
        )
        if total_transactions == 0:
            return 0.0
        
        rate = float(state.transaction_failure_count) / total_transactions
        return min(rate, 1.0)
    
    def _compute_error_cascade(self, state: WindowsServerState) -> float:
        """Compute error cascade indicator (5+ consecutive errors)"""
        if state.max_consecutive_errors >= 5:
            # Normalize cascade intensity
            normalized = min(
                float(state.max_consecutive_errors) / self.MAX_CONSECUTIVE_ERRORS,
                1.0
            )
            return normalized
        return 0.0
    
    def _compute_hresult_bucket(self, state: WindowsServerState) -> float:
        """Compute HRESULT code bucket diversity"""
        if state.total_errors == 0:
            return 0.0
        
        unique_hresults = len(state.error_hresults)
        # Normalize: more hresult codes = higher anomaly
        normalized = min(
            float(unique_hresults) / self.MAX_HRESULT_BUCKET,
            1.0
        )
        return normalized
    
    def _compute_service_health_transition(self, state: WindowsServerState) -> float:
        """Compute service health transition score"""
        if state.service_state_transitions > 3:
            # Multiple transitions indicate instability
            normalized = min(
                float(state.service_state_transitions) / 6.0,
                1.0
            )
            return normalized
        return 0.0
    
    def _compute_package_failure_rate(self, state: WindowsServerState) -> float:
        """Compute package install failure rate"""
        total_package_events = (
            state.event_type_counts.get("package_applicability", 0) +
            state.event_type_counts.get("package_error", 0)
        )
        
        if total_package_events == 0:
            return 0.0
        
        failure_count = sum(state.package_errors.values())
        rate = float(failure_count) / (total_package_events + 1)
        return min(rate, 1.0)
    
    def _compute_consecutive_errors_normalized(self, state: WindowsServerState) -> float:
        """Compute normalized consecutive errors"""
        normalized = min(
            float(state.consecutive_errors) / self.MAX_CONSECUTIVE_ERRORS,
            1.0
        )
        return normalized
    
    def _compute_temporal_irregularity(self, state: WindowsServerState, log_time: datetime) -> float:
        """Compute temporal irregularity based on event timing"""
        if state.last_event_time is None or len(state.event_timestamp_queue) < 2:
            return 0.0
        
        # Very recent event is less irregular
        time_since_last = (log_time - state.last_event_time).total_seconds()
        
        # If more than 1 hour, indicate irregularity
        if time_since_last > self.WINDOW_1H:
            return 1.0
        elif time_since_last > self.WINDOW_10M:
            return 0.5
        else:
            return 0.0
    
    def _compute_overall_anomaly_score(self, features: List[float]) -> float:
        """
        Compute overall anomaly score from individual features.
        
        Weights anomalies from cascade, error rate, and transitions.
        """
        # Use select high-value features for anomaly computation
        # Feature 2: error_rate_5m
        # Feature 4: error_cascade_indicator
        # Feature 6: service_health_transition
        # Feature 7: package_failure_rate
        # Feature 9: consecutive_errors_normalized
        
        anomaly_features = [
            features[2],   # error_rate_5m
            features[4],   # error_cascade_indicator
            features[6],   # service_health_transition
            features[7],   # package_failure_rate
            features[9],   # consecutive_errors_normalized
        ]
        
        # Average the anomaly signals
        if not anomaly_features:
            return 0.0
        
        overall = sum(anomaly_features) / len(anomaly_features)
        return min(overall, 1.0)
