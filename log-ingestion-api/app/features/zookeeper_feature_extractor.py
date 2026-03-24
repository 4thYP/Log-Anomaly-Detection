"""
STEP 4: Stateful feature extractor for Zookeeper consensus logs.
Tracks per-server behavioral patterns with fixed 10-element feature vectors.
"""

from collections import defaultdict, deque
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from enum import IntEnum

from app.models.log_models import LogInternal


class ZookeeperEventTypeCode(IntEnum):
    """Numeric encoding for Zookeeper event types"""
    CONNECTION_RECEIVED = 1
    CONNECTION_BROKEN = 2
    WORKER_SEND_LEAVING = 3
    WORKER_INTERRUPTED = 4
    WORKER_INTERRUPT_SEND = 5
    SESSION_ESTABLISHED = 6
    SESSION_EXPIRED = 7
    ELECTION_NOTIFICATION = 8
    ELECTION_STATE_CHANGE = 9
    ELECTION_NOTIFICATION_TIMEOUT = 10
    QUORUM_ACHIEVED = 11
    QUORUM_LOST = 12
    SERVER_INITIALIZED = 13
    SERVER_SHUTDOWN = 14
    PEER_SYNC = 15
    UNKNOWN = 16


class ZookeeperServerState:
    """Per-server state for Zookeeper feature extraction (STEP 4)"""
    
    def __init__(self, max_queue_size: int = 1000):
        """Initialize per-server state tracking"""
        # Event frequency tracking
        self.event_timestamp_queue: deque = deque(maxlen=max_queue_size)
        self.event_type_counts: Dict[str, int] = defaultdict(int)
        
        # Connection tracking
        self.connections_received: int = 0
        self.connections_broken: int = 0
        self.consecutive_connection_breaks: int = 0
        self.max_consecutive_breaks: int = 0
        
        # Worker tracking
        self.worker_send_leaves: int = 0
        self.worker_interruptions: int = 0
        self.worker_churn_events: deque = deque(maxlen=100)
        self.active_send_workers: set = set()
        self.active_recv_workers: set = set()
        
        # Session tracking
        self.sessions_established: int = 0
        self.sessions_expired: int = 0
        self.active_sessions: set = set()
        self.session_timeout_events: deque = deque(maxlen=50)
        
        # Quorum tracking
        self.election_notifications: int = 0
        self.election_state_changes: int = 0
        self.notification_timeouts: int = 0
        self.have_quorum_count: int = 0
        self.quorum_lost_count: int = 0
        self.quorum_events: deque = deque(maxlen=100)
        self.last_election_state: Optional[str] = None
        
        # Error tracking
        self.error_events: int = 0
        self.consecutive_errors: int = 0
        self.max_consecutive_errors: int = 0
        self.error_types: Dict[str, int] = defaultdict(int)
        
        # Temporal state
        self.total_events: int = 0
        self.last_event_time: Optional[datetime] = None


class ZookeeperFeatureExtractor:
    """
    Stateful feature extractor for Zookeeper consensus logs (STEP 4 design).
    
    Per-server state isolation:
    - Maintains separate state for each server (sid)
    - Uses log_internal.timestamp (not datetime.now())
    - Returns fixed 10-element feature vector
    - All features normalized to [0, 1]
    """
    
    # Time windows (in seconds)
    WINDOW_5M = 300
    WINDOW_10M = 600
    WINDOW_1H = 3600
    
    # Normalization constants
    MAX_EVENT_TYPE = 16  # ZookeeperEventTypeCode.UNKNOWN
    MAX_CONSECUTIVE_ERRORS = 20
    MAX_CONSECUTIVE_BREAKS = 10
    MAX_WORKER_CHURN = 100
    
    def __init__(self, max_queue_size: int = 1000):
        """
        Initialize the feature extractor.
        
        Args:
            max_queue_size: Maximum size for per-server event queues
        """
        self.max_queue_size = max_queue_size
        # Per-server state storage: sid -> ZookeeperServerState
        self.server_states: Dict[str, ZookeeperServerState] = {}
    
    def _get_or_create_server_state(self, sid: str) -> ZookeeperServerState:
        """Get or create state for a specific server"""
        if sid not in self.server_states:
            self.server_states[sid] = ZookeeperServerState(self.max_queue_size)
        return self.server_states[sid]


    def extract(self, log_internal: LogInternal) -> List[float]:
        """
        Extract 10-element feature vector from a LogInternal object.
        
        STEP 4 Interface:
        - Uses log_internal.sid for per-server state
        - Uses log_internal.timestamp (NOT datetime.now())
        - Returns List[float] with exactly 10 normalized values
        
        Args:
            log_internal: LogInternal object with parsed data in metadata["parsed"]
            
        Returns:
            List of 10 floats, each in [0, 1] range
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
        
        # Compute 10-element feature vector
        features = self._compute_feature_vector(parsed_log, state, log_time)
        
        # Verify constraints
        assert len(features) == 10, f"Expected 10 features, got {len(features)}"
        assert all(isinstance(f, (int, float)) for f in features), "All features must be numeric"
        assert all(0 <= f <= 1 for f in features), f"All features must be in [0, 1], got {features}"
        
        return features

    
    # ============================================================================
    # STATE UPDATE
    # ============================================================================
    
    def _update_server_state(
        self,
        parsed_log: Dict[str, Any],
        state: ZookeeperServerState,
        log_time: datetime
    ) -> None:
        """
        Update per-server state with current event.
        
        Args:
            parsed_log: Dictionary with event data
            state: ZookeeperServerState for this server
            log_time: Timestamp from log (NOT datetime.now())
        """
        state.total_events += 1
        
        event_type = parsed_log.get("event_type", "unknown")
        status = parsed_log.get("status", "info")
        
        # Update counters
        state.event_type_counts[event_type] += 1
        state.event_timestamp_queue.append(log_time)
        state.last_event_time = log_time
        
        # Update error tracking
        if status in ["failure", "error"]:
            state.error_events += 1
            state.consecutive_errors += 1
            state.max_consecutive_errors = max(
                state.max_consecutive_errors, state.consecutive_errors
            )
            
            error_type = parsed_log.get("error_reason", event_type)
            state.error_types[error_type] += 1
        else:
            state.consecutive_errors = 0
        
        # Connection events
        if event_type == "connection_received":
            state.connections_received += 1
            state.consecutive_connection_breaks = 0
        
        elif event_type == "connection_broken":
            state.connections_broken += 1
            state.consecutive_connection_breaks += 1
            state.max_consecutive_breaks = max(
                state.max_consecutive_breaks, state.consecutive_connection_breaks
            )
        
        # Worker events
        if event_type == "worker_send_leaving":
            state.worker_send_leaves += 1
            state.worker_churn_events.append(("send_leave", log_time))
            socket_id = parsed_log.get("socket_id")
            if socket_id:
                state.active_send_workers.discard(socket_id)
        
        elif event_type in ["worker_interrupted", "worker_interrupt_send"]:
            state.worker_interruptions += 1
            state.worker_churn_events.append((event_type, log_time))
        
        # Session events
        if event_type == "session_established":
            state.sessions_established += 1
            session_id = parsed_log.get("session_id")
            if session_id:
                state.active_sessions.add(session_id)
        
        elif event_type == "session_expired":
            state.sessions_expired += 1
            session_id = parsed_log.get("session_id")
            if session_id:
                state.active_sessions.discard(session_id)
                timeout_ms = parsed_log.get("timeout_ms", 0)
                state.session_timeout_events.append((log_time, timeout_ms))
        
        # Quorum/Election events
        if event_type == "election_notification":
            state.election_notifications += 1
            state.quorum_events.append(("notification", log_time))
        
        elif event_type == "election_state_change":
            state.election_state_changes += 1
            new_state = parsed_log.get("election_state")
            if new_state:
                state.last_election_state = new_state
            state.quorum_events.append(("state_change", log_time))
        
        elif event_type == "election_notification_timeout":
            state.notification_timeouts += 1
            state.quorum_events.append(("timeout", log_time))
        
        elif event_type == "quorum_achieved":
            state.have_quorum_count += 1
            state.quorum_events.append(("quorum_achieved", log_time))
        
        elif event_type == "quorum_lost":
            state.quorum_lost_count += 1
            state.quorum_events.append(("quorum_lost", log_time))

    
    # ============================================================================
    # FEATURE COMPUTATION
    # ============================================================================
    
    def _compute_feature_vector(
        self,
        parsed_log: Dict[str, Any],
        state: ZookeeperServerState,
        log_time: datetime
    ) -> List[float]:
        """
        Compute 10-element normalized feature vector.
        
        FEATURE ORDER (must match specification):
        0. event_type_code (1-16, normalized to 0-1)
        1. connection_churn_rate (0-1)
        2. worker_instability (0-1)
        3. election_frequency (0-1)
        4. session_timeout_rate (0-1)
        5. quorum_health (0-1)
        6. error_event_rate (0-1)
        7. is_error_flag (0 or 1)
        8. consensus_lag_indicator (0-1)
        9. overall_anomaly_score (0-1)
        """
        event_type = parsed_log.get("event_type", "unknown")
        status = parsed_log.get("status", "info")
        
        features = []
        
        # Feature 0: event_type_code (1-16, normalized to 0-1)
        event_code = self._encode_event_type(event_type)
        feature_0 = float(event_code) / self.MAX_EVENT_TYPE
        features.append(min(feature_0, 1.0))
        
        # Feature 1: connection_churn_rate (0-1)
        feature_1 = self._compute_connection_churn_rate(state, log_time)
        features.append(feature_1)
        
        # Feature 2: worker_instability (0-1)
        feature_2 = self._compute_worker_instability(state)
        features.append(feature_2)
        
        # Feature 3: election_frequency (0-1)
        feature_3 = self._compute_election_frequency(state, log_time)
        features.append(feature_3)
        
        # Feature 4: session_timeout_rate (0-1)
        feature_4 = self._compute_session_timeout_rate(state)
        features.append(feature_4)
        
        # Feature 5: quorum_health (0-1)
        feature_5 = self._compute_quorum_health(state)
        features.append(feature_5)
        
        # Feature 6: error_event_rate (0-1)
        feature_6 = self._compute_error_event_rate(state)
        features.append(feature_6)
        
        # Feature 7: is_error_flag (0 or 1)
        feature_7 = 1.0 if status in ["failure", "error"] else 0.0
        features.append(feature_7)
        
        # Feature 8: consensus_lag_indicator (0-1)
        feature_8 = self._compute_consensus_lag_indicator(state, log_time)
        features.append(feature_8)
        
        # Feature 9: overall_anomaly_score (0-1)
        feature_9 = self._compute_overall_anomaly_score(features)
        features.append(feature_9)
        
        return features
    
    # ============================================================================
    # HELPER COMPUTATION METHODS
    # ============================================================================
    
    def _encode_event_type(self, event_type: str) -> int:
        """Encode event type string to numeric code"""
        mapping = {
            "connection_received": ZookeeperEventTypeCode.CONNECTION_RECEIVED,
            "connection_broken": ZookeeperEventTypeCode.CONNECTION_BROKEN,
            "worker_send_leaving": ZookeeperEventTypeCode.WORKER_SEND_LEAVING,
            "worker_interrupted": ZookeeperEventTypeCode.WORKER_INTERRUPTED,
            "worker_interrupt_send": ZookeeperEventTypeCode.WORKER_INTERRUPT_SEND,
            "session_established": ZookeeperEventTypeCode.SESSION_ESTABLISHED,
            "session_expired": ZookeeperEventTypeCode.SESSION_EXPIRED,
            "election_notification": ZookeeperEventTypeCode.ELECTION_NOTIFICATION,
            "election_state_change": ZookeeperEventTypeCode.ELECTION_STATE_CHANGE,
            "election_notification_timeout": ZookeeperEventTypeCode.ELECTION_NOTIFICATION_TIMEOUT,
            "quorum_achieved": ZookeeperEventTypeCode.QUORUM_ACHIEVED,
            "quorum_lost": ZookeeperEventTypeCode.QUORUM_LOST,
            "server_initialized": ZookeeperEventTypeCode.SERVER_INITIALIZED,
            "server_shutdown": ZookeeperEventTypeCode.SERVER_SHUTDOWN,
            "peer_sync": ZookeeperEventTypeCode.PEER_SYNC,
        }
        return mapping.get(event_type, ZookeeperEventTypeCode.UNKNOWN)
    
    def _compute_connection_churn_rate(self, state: ZookeeperServerState, log_time: datetime) -> float:
        """Compute connection churn rate (broken connections)"""
        total_conn_events = state.connections_received + state.connections_broken
        if total_conn_events == 0:
            return 0.0
        
        churn_rate = float(state.connections_broken) / total_conn_events
        return min(churn_rate, 1.0)
    
    def _compute_worker_instability(self, state: ZookeeperServerState) -> float:
        """Compute worker instability from churn events"""
        if len(state.worker_churn_events) == 0:
            return 0.0
        
        # Normalize churn events to [0, 1]
        normalized = min(
            float(len(state.worker_churn_events)) / self.MAX_WORKER_CHURN,
            1.0
        )
        return normalized
    
    def _compute_election_frequency(self, state: ZookeeperServerState, log_time: datetime) -> float:
        """Compute election frequency in recent window"""
        window_start = log_time - timedelta(seconds=self.WINDOW_5M)
        
        # Count quorum events in window
        recent_election_events = sum(
            1 for _, ts in state.quorum_events if ts >= window_start
        )
        
        # Normalize: high frequency = anomaly
        # Typical: 0-5 events in 5 minutes
        normalized = min(float(recent_election_events) / 10.0, 1.0)
        return normalized
    
    def _compute_session_timeout_rate(self, state: ZookeeperServerState) -> float:
        """Compute session timeout rate"""
        total_sessions = state.sessions_established + state.sessions_expired
        if total_sessions == 0:
            return 0.0
        
        timeout_rate = float(state.sessions_expired) / total_sessions
        return min(timeout_rate, 1.0)
    
    def _compute_quorum_health(self, state: ZookeeperServerState) -> float:
        """Compute quorum health (opposite of quorum lost events)"""
        total_quorum_events = (
            state.have_quorum_count + state.quorum_lost_count +
            state.election_notifications + state.notification_timeouts
        )
        
        if total_quorum_events == 0:
            return 1.0  # Healthy if no quorum events
        
        # Health inversely proportional to quorum loss and timeouts
        loss_and_timeouts = state.quorum_lost_count + state.notification_timeouts
        health = 1.0 - (float(loss_and_timeouts) / total_quorum_events)
        return max(min(health, 1.0), 0.0)
    
    def _compute_error_event_rate(self, state: ZookeeperServerState) -> float:
        """Compute error event rate"""
        if state.total_events == 0:
            return 0.0
        
        error_rate = float(state.error_events) / state.total_events
        return min(error_rate, 1.0)
    
    def _compute_consensus_lag_indicator(self, state: ZookeeperServerState, log_time: datetime) -> float:
        """Compute consensus lag based on consecutive connection breaks and timeouts"""
        # Combine connection breaks and election timeouts as lag indicators
        has_breaks = state.consecutive_connection_breaks > 0
        has_timeouts = state.notification_timeouts > 0
        
        lag_score = 0.0
        
        if has_breaks:
            # Normalize consecutive breaks
            lag_score += min(
                float(state.consecutive_connection_breaks) / self.MAX_CONSECUTIVE_BREAKS,
                1.0
            )
        
        if has_timeouts:
            # Add timeout component
            lag_score += 0.3
        
        return min(lag_score, 1.0)
    
    def _compute_overall_anomaly_score(self, features: List[float]) -> float:
        """
        Compute overall anomaly score from individual features.
        
        Weights anomalies from connection churn, worker instability,
        election frequency, and error rate.
        """
        # Use select high-value anomaly features
        # Feature 1: connection_churn_rate
        # Feature 2: worker_instability
        # Feature 3: election_frequency
        # Feature 4: session_timeout_rate
        # Feature 6: error_event_rate
        # Feature 8: consensus_lag_indicator
        
        anomaly_features = [
            features[1],   # connection_churn_rate
            features[2],   # worker_instability
            features[3],   # election_frequency
            features[4],   # session_timeout_rate
            features[6],   # error_event_rate
            features[8],   # consensus_lag_indicator
        ]
        
        # Average the anomaly signals
        if not anomaly_features:
            return 0.0
        
        overall = sum(anomaly_features) / len(anomaly_features)
        return min(overall, 1.0)
