"""
Production-grade Zookeeper feature extractor for anomaly detection.
Stateful extraction of 50+ numeric features from parsed Zookeeper logs.
"""

from collections import defaultdict, deque
from typing import Dict, Optional, Any, Set
from datetime import datetime

from app.models.log_models import LogInternal


class ZookeeperFeatureExtractor:
    """
    Stateful feature extractor for Zookeeper distributed consensus logs.

    Maintains state across events to compute:
    - Connection establishment and failure patterns
    - Worker lifecycle and churn indicators
    - Quorum consensus health and leader election stability
    - Session lifecycle and timeout patterns
    - Error clustering and cascade detection
    - Temporal anomaly signals

    Features are designed for ML-based anomaly detection.
    Output: Dict[str, float] with 50+ numeric features.
    """

    # Singleton instance for state preservation across requests
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ZookeeperFeatureExtractor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize feature extractor with state tracking"""
        if self._initialized:
            return

        # Event frequency tracking
        self.event_type_counts: Dict[str, int] = defaultdict(int)
        self.component_counts: Dict[str, int] = defaultdict(int)
        self.status_counts: Dict[str, int] = defaultdict(int)

        # Connection tracking
        self.connections_received: int = 0
        self.connections_broken: int = 0
        self.connection_errors: deque = deque(maxlen=50)
        self.consecutive_connection_breaks: int = 0
        self.max_consecutive_breaks: int = 0

        # Worker tracking
        self.worker_send_leaves: int = 0
        self.worker_interruptions: int = 0
        self.worker_churn_recent: deque = deque(maxlen=100)
        self.active_send_workers: Set[str] = set()
        self.active_recv_workers: Set[str] = set()

        # Session tracking
        self.sessions_established: int = 0
        self.sessions_expired: int = 0
        self.active_sessions: Set[str] = set()
        self.session_timeout_events: deque = deque(maxlen=50)

        # Quorum tracking
        self.election_notifications: int = 0
        self.election_state_changes: int = 0
        self.notification_timeouts: int = 0
        self.have_quorum_count: int = 0
        self.last_election_state: Optional[str] = None
        self.quorum_stability_events: deque = deque(maxlen=100)

        # Error tracking
        self.error_events: int = 0
        self.error_types: Dict[str, int] = defaultdict(int)
        self.error_cascade_raw: deque = deque(maxlen=100)
        self.consecutive_errors: int = 0
        self.max_consecutive_errors: int = 0

        # Temporal tracking
        self.total_events: int = 0
        self.last_event_time: Optional[float] = None
        self.event_rate_5m: deque = deque(maxlen=300)

        # Network/Peer tracking
        self.unique_peers: Set[str] = set()
        self.peer_failure_count: Dict[str, int] = defaultdict(int)
        self.ip_addresses: Set[str] = set()

        # Anomaly indicators
        self.connection_burst_indicator: float = 0.0
        self.worker_churn_indicator: float = 0.0
        self.election_instability_indicator: float = 0.0
        self.error_spike_indicator: float = 0.0

        self._initialized = True

    def extract(self, log_internal: LogInternal) -> Dict[str, float]:
        """
        Extract features from a single parsed event.

        Args:
            log_internal: LogInternal object with metadata["parsed"]

        Returns:
            Dictionary of numeric features suitable for ML models
        """
        # Get parsed event
        parsed = log_internal.metadata.get("parsed", {})
        if not parsed:
            return self._get_baseline_features()

        # Update state
        self._update_state(parsed)

        # Compute features
        features = {}

        # Basic frequency features
        features.update(self._extract_frequency_features())

        # Connection features
        features.update(self._extract_connection_features())

        # Worker features
        features.update(self._extract_worker_features())

        # Session features
        features.update(self._extract_session_features())

        # Quorum/Election features
        features.update(self._extract_quorum_features())

        # Error features
        features.update(self._extract_error_features())

        # Temporal features
        features.update(self._extract_temporal_features())

        # Peer/Network features
        features.update(self._extract_peer_features())

        # Anomaly indicators
        features.update(self._extract_anomaly_features())

        return features

    # ============================================================================
    # STATE UPDATE
    # ============================================================================

    def _update_state(self, parsed: Dict[str, Any]) -> None:
        """Update internal state with new event"""
        self.total_events += 1

        event_type = parsed.get("event_type", "unknown")
        component = parsed.get("component", "unknown")
        status = parsed.get("status", "info")
        level = parsed.get("level", "INFO")

        # Update counters
        self.event_type_counts[event_type] += 1
        self.component_counts[component] += 1
        self.status_counts[status] += 1

        # Connection events
        if event_type == "connection_received":
            self.connections_received += 1
            remote_ip = parsed.get("remote_ip", "unknown")
            if remote_ip:
                self.ip_addresses.add(remote_ip)

        elif event_type == "connection_broken":
            self.connections_broken += 1
            self.consecutive_connection_breaks += 1
            self.max_consecutive_breaks = max(
                self.max_consecutive_breaks, self.consecutive_connection_breaks
            )
            self.connection_errors.append(
                (datetime.now().timestamp(), parsed.get("error_reason"))
            )
            peer_id = parsed.get("peer_id")
            if peer_id:
                self.peer_failure_count[str(peer_id)] += 1
        else:
            self.consecutive_connection_breaks = 0

        # Worker events
        if event_type == "worker_send_leaving":
            self.worker_send_leaves += 1
            self.worker_churn_recent.append(("send_leave", datetime.now().timestamp()))
            socket_id = parsed.get("socket_id")
            if socket_id:
                self.active_send_workers.discard(socket_id)

        elif event_type == "worker_interrupted":
            self.worker_interruptions += 1
            self.worker_churn_recent.append(
                ("interrupted", datetime.now().timestamp())
            )

        elif event_type == "worker_interrupt_send":
            self.worker_interruptions += 1
            self.worker_churn_recent.append(
                ("interrupt_send", datetime.now().timestamp())
            )

        # Session events
        if event_type == "session_established":
            self.sessions_established += 1
            session_id = parsed.get("session_id")
            if session_id:
                self.active_sessions.add(session_id)

        elif event_type == "session_expired":
            self.sessions_expired += 1
            session_id = parsed.get("session_id")
            if session_id:
                self.active_sessions.discard(session_id)
                self.session_timeout_events.append(
                    (datetime.now().timestamp(), parsed.get("timeout_ms", 0))
                )

        # Quorum/Election events
        if event_type == "election_notification":
            self.election_notifications += 1
            self.quorum_stability_events.append(
                ("notification", datetime.now().timestamp())
            )

        elif event_type == "election_state_change":
            self.election_state_changes += 1
            new_state = parsed.get("election_state")
            if new_state:
                self.last_election_state = new_state
            self.quorum_stability_events.append(
                ("state_change", datetime.now().timestamp())
            )

        elif event_type == "election_notification_timeout":
            self.notification_timeouts += 1
            self.quorum_stability_events.append(
                ("timeout", datetime.now().timestamp())
            )

        elif event_type == "quorum_achieved":
            self.have_quorum_count += 1
            self.quorum_stability_events.append(
                ("quorum_achieved", datetime.now().timestamp())
            )

        # Error events
        if status in ["failure", "error"]:
            self.error_events += 1
            self.consecutive_errors += 1
            self.max_consecutive_errors = max(
                self.max_consecutive_errors, self.consecutive_errors
            )

            error_type = parsed.get("error_reason", event_type)
            self.error_types[error_type] += 1
            self.error_cascade_raw.append(error_type)
        else:
            self.consecutive_errors = 0

        # Peer tracking
        peer_id = parsed.get("peer_id")
        if peer_id:
            self.unique_peers.add(str(peer_id))

        # Temporal update
        self.last_event_time = datetime.now().timestamp()

    # ============================================================================
    # FEATURE EXTRACTION METHODS
    # ============================================================================

    def _extract_frequency_features(self) -> Dict[str, float]:
        """Basic event frequency features"""
        features = {}

        # Event type frequencies
        features["event_count_total"] = float(self.total_events)
        features["event_count_connection_received"] = float(
            self.event_type_counts["connection_received"]
        )
        features["event_count_connection_broken"] = float(
            self.event_type_counts["connection_broken"]
        )
        features["event_count_worker_send_leaving"] = float(
            self.event_type_counts["worker_send_leaving"]
        )
        features["event_count_worker_interrupted"] = float(
            self.event_type_counts["worker_interrupted"]
        )
        features["event_count_election_notification"] = float(
            self.event_type_counts["election_notification"]
        )
        features["event_count_session_established"] = float(
            self.event_type_counts["session_established"]
        )
        features["event_count_session_expired"] = float(
            self.event_type_counts["session_expired"]
        )

        # Level distribution
        features["level_info_count"] = float(self.status_counts["info"])
        features["level_warn_count"] = float(self.status_counts["warning"])
        features["level_error_count"] = float(self.status_counts["failure"])

        return features

    def _extract_connection_features(self) -> Dict[str, float]:
        """Connection management features"""
        features = {}

        features["connection_received_count"] = float(self.connections_received)
        features["connection_broken_count"] = float(self.connections_broken)
        features["connection_consecutive_breaks_max"] = float(
            self.max_consecutive_breaks
        )

        # Connection error rate
        total_connection_events = self.connections_received + self.connections_broken
        if total_connection_events > 0:
            features["connection_break_rate"] = (
                self.connections_broken / total_connection_events
            )
        else:
            features["connection_break_rate"] = 0.0

        # Connection health
        features["connection_health"] = (
            1.0 - features["connection_break_rate"]
        ) if total_connection_events > 0 else 1.0

        return features

    def _extract_worker_features(self) -> Dict[str, float]:
        """Worker lifecycle and churn features"""
        features = {}

        features["worker_send_leaves_count"] = float(self.worker_send_leaves)
        features["worker_interruptions_count"] = float(self.worker_interruptions)
        features["worker_active_send_count"] = float(len(self.active_send_workers))
        features["worker_active_recv_count"] = float(len(self.active_recv_workers))

        # Worker churn rate (events in last 100)
        if len(self.worker_churn_recent) > 0:
            features["worker_churn_rate"] = len(self.worker_churn_recent) / 100.0
        else:
            features["worker_churn_rate"] = 0.0

        # Total worker activity
        features["worker_total_activity"] = float(
            self.worker_send_leaves + self.worker_interruptions
        )

        return features

    def _extract_session_features(self) -> Dict[str, float]:
        """Session lifecycle features"""
        features = {}

        features["session_established_count"] = float(self.sessions_established)
        features["session_expired_count"] = float(self.sessions_expired)
        features["session_active_count"] = float(len(self.active_sessions))

        # Session success rate
        total_sessions = self.sessions_established + self.sessions_expired
        if total_sessions > 0:
            features["session_success_rate"] = (
                self.sessions_established / total_sessions
            )
        else:
            features["session_success_rate"] = 0.0

        # Average session timeout (from expired sessions)
        if len(self.session_timeout_events) > 0:
            avg_timeout = sum(t[1] for t in self.session_timeout_events) / len(
                self.session_timeout_events
            )
            features["session_timeout_average"] = float(avg_timeout)
        else:
            features["session_timeout_average"] = 0.0

        return features

    def _extract_quorum_features(self) -> Dict[str, float]:
        """Quorum consensus and leader election features"""
        features = {}

        features["election_notification_count"] = float(self.election_notifications)
        features["election_state_change_count"] = float(self.election_state_changes)
        features["election_notification_timeout_count"] = float(
            self.notification_timeouts
        )
        features["quorum_achieved_count"] = float(self.have_quorum_count)

        # Election stability (high = stable, low = unstable)
        total_election_events = (
            self.election_notifications
            + self.election_state_changes
            + self.notification_timeouts
        )
        if total_election_events > 0:
            stable_events = self.have_quorum_count
            features["election_stability"] = (
                stable_events / max(total_election_events, 1)
            )
        else:
            features["election_stability"] = 1.0

        # Quorum events in recent window
        if len(self.quorum_stability_events) > 0:
            features["quorum_activity_recent"] = float(
                len(self.quorum_stability_events)
            )
        else:
            features["quorum_activity_recent"] = 0.0

        return features

    def _extract_error_features(self) -> Dict[str, float]:
        """Error patterns and classification"""
        features = {}

        features["error_count_total"] = float(self.error_events)
        features["error_consecutive_max"] = float(self.max_consecutive_errors)

        # Error rate
        error_rate = 0.0
        if self.total_events > 0:
            error_rate = self.error_events / self.total_events
        features["error_rate"] = error_rate

        # Error cascade (5+ consecutive errors)
        features["error_cascade_indicator"] = (
            1.0 if self.max_consecutive_errors >= 5 else 0.0
        )

        # Error type distribution
        features["error_type_unique_count"] = float(len(self.error_types))

        # Most common error
        if self.error_types:
            most_common_error_count = max(self.error_types.values())
            features["error_type_max_frequency"] = float(most_common_error_count)
            features["error_type_concentration"] = (
                most_common_error_count / self.error_events
            ) if self.error_events > 0 else 0.0
        else:
            features["error_type_max_frequency"] = 0.0
            features["error_type_concentration"] = 0.0

        return features

    def _extract_temporal_features(self) -> Dict[str, float]:
        """Time-window and recency features"""
        features = {}

        # Recency
        if self.last_event_time:
            recency = datetime.now().timestamp() - self.last_event_time
            features["event_recency_seconds"] = max(recency, 0.0)
        else:
            features["event_recency_seconds"] = 0.0

        # Event rate (approximation from recent activity)
        features["event_rate_5m_approx"] = float(len(self.event_rate_5m) / 300.0)

        return features

    def _extract_peer_features(self) -> Dict[str, float]:
        """Network peer and host tracking"""
        features = {}

        features["peer_unique_count"] = float(len(self.unique_peers))
        features["ip_unique_count"] = float(len(self.ip_addresses))

        # Peer failure clustering
        if self.peer_failure_count:
            max_peer_failures = max(self.peer_failure_count.values())
            features["peer_failure_max"] = float(max_peer_failures)
            features["peer_failure_concentration"] = (
                max_peer_failures / self.connections_broken
            ) if self.connections_broken > 0 else 0.0
        else:
            features["peer_failure_max"] = 0.0
            features["peer_failure_concentration"] = 0.0

        return features

    def _extract_anomaly_features(self) -> Dict[str, float]:
        """High-level anomaly indicators"""
        features = {}

        # Error rate (for use in anomaly detection)
        error_rate = 0.0
        if self.total_events > 0:
            error_rate = self.error_events / self.total_events

        # Connection burst (multiple broken connections)
        if self.max_consecutive_breaks > 3:
            features["anomaly_connection_burst"] = 1.0
        else:
            features["anomaly_connection_burst"] = 0.0

        # Worker churn (high rate of worker interruptions)
        if features.get("worker_churn_rate", 0.0) > 0.5:
            features["anomaly_worker_churn"] = 1.0
        else:
            features["anomaly_worker_churn"] = 0.0

        # Election instability (rapid state changes without quorum)
        if (
            self.election_state_changes > 5
            and self.have_quorum_count < self.election_state_changes / 2
        ):
            features["anomaly_election_instability"] = 1.0
        else:
            features["anomaly_election_instability"] = 0.0

        # Error spike
        if error_rate > 0.2 and self.error_events > 5:
            features["anomaly_error_spike"] = 1.0
        else:
            features["anomaly_error_spike"] = 0.0

        # Error cascade
        features["anomaly_error_cascade"] = (
            1.0 if self.max_consecutive_errors >= 5 else 0.0
        )

        # Composite anomaly score
        anomaly_signals = [
            features.get("anomaly_connection_burst", 0.0),
            features.get("anomaly_worker_churn", 0.0),
            features.get("anomaly_election_instability", 0.0),
            features.get("anomaly_error_spike", 0.0),
            features.get("anomaly_error_cascade", 0.0),
        ]
        features["anomaly_score"] = sum(anomaly_signals) / len(anomaly_signals)

        return features

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def _get_baseline_features(self) -> Dict[str, float]:
        """Return baseline/missing feature vector"""
        return {
            "event_count_total": 0.0,
            "error_count_total": 0.0,
            "error_rate": 0.0,
            "anomaly_score": 0.0,
        }

    def reset_state(self) -> None:
        """Reset all state (for testing or new dataset)"""
        self.__init__()
        self._initialized = False


# Singleton factory
def get_zookeeper_feature_extractor() -> ZookeeperFeatureExtractor:
    """Get or create Zookeeper feature extractor instance"""
    return ZookeeperFeatureExtractor()
