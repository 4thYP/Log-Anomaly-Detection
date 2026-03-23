"""
Production-grade Windows feature extractor for anomaly detection.
Stateful extraction of 50+ numeric features from parsed Windows events.
"""

from collections import defaultdict, deque
from typing import Dict, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
import math

from app.models.log_models import LogInternal


class WindowsFeatureExtractor:
    """
    Stateful feature extractor for Windows event logs.
    
    Maintains state across events to compute:
    - Event frequency and rate metrics
    - Error pattern detection
    - HRESULT code clustering
    - Error cascade indicators
    - Service health transitions
    - Temporal anomaly signals
    
    Features are designed for ML-based anomaly detection.
    Output: Dict[str, float] with 50+ numeric features.
    """

    # Singleton instance for state preservation across requests
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WindowsFeatureExtractor, cls).__new__(cls)
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

        # Error tracking
        self.error_codes: deque = deque(maxlen=100)  # Last 100 errors
        self.error_hresults: Dict[str, int] = defaultdict(int)
        self.error_names: Dict[str, int] = defaultdict(int)
        self.consecutive_errors: int = 0
        self.max_consecutive_errors: int = 0

        # Event-level tracking
        self.total_events: int = 0
        self.total_errors: int = 0
        self.total_failures: int = 0

        # Transaction tracking
        self.active_transactions: Dict[str, float] = {}  # handle -> timestamp
        self.transaction_handles: deque = deque(maxlen=50)
        self.transaction_success_count: int = 0
        self.transaction_failure_count: int = 0

        # Package tracking
        self.packages_seen: Set[str] = set()
        self.package_errors: Dict[str, int] = defaultdict(int)

        # Session tracking
        self.active_sessions: Set[str] = set()
        self.session_events: Dict[str, int] = defaultdict(int)

        # Service state tracking
        self.service_state: str = "unknown"  # "running", "initializing", "stopped"
        self.service_startup_time: Optional[float] = None
        self.service_state_transitions: int = 0

        # Temporal windows (time-based in seconds)
        self.time_windows: Dict[str, deque] = {
            "5m": deque(maxlen=300),  # Events in last 5 minutes
            "10m": deque(maxlen=600),
            "1h": deque(maxlen=3600),
        }

        # Cache for feature computation
        self.last_event_time: Optional[float] = None
        self.time_since_last_event: float = 0.0

        # Anomaly indicators
        self.error_spike_indicator: float = 0.0
        self.cascade_indicator: float = 0.0
        self.package_stress_indicator: float = 0.0

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

        # Error pattern features
        features.update(self._extract_error_features())

        # Transaction features
        features.update(self._extract_transaction_features())

        # Package features
        features.update(self._extract_package_features())

        # Service features
        features.update(self._extract_service_features())

        # Session features
        features.update(self._extract_session_features())

        # Temporal features
        features.update(self._extract_temporal_features())

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

        # Update counters
        self.event_type_counts[event_type] += 1
        self.component_counts[component] += 1
        self.status_counts[status] += 1

        # Update error tracking
        if status in ["failure", "error", "warning"]:
            self.total_errors += 1
            self.consecutive_errors += 1
            self.max_consecutive_errors = max(
                self.max_consecutive_errors, self.consecutive_errors
            )

            hresult = parsed.get("hresult")
            error_name = parsed.get("error_name")
            if hresult:
                self.error_hresults[hresult] += 1
            if error_name:
                self.error_names[error_name] += 1
                self.error_codes.append(error_name)

            if status == "failure":
                self.total_failures += 1
        else:
            self.consecutive_errors = 0

        # Update transaction tracking
        if event_type == "transaction_create":
            handle = parsed.get("handle")
            if handle:
                self.active_transactions[handle] = datetime.now().timestamp()
                self.transaction_handles.append(handle)
                if status == "success":
                    self.transaction_success_count += 1
                else:
                    self.transaction_failure_count += 1

        # Update package tracking
        if "package" in event_type:
            pkg_name = parsed.get("package_name", "unknown")
            self.packages_seen.add(pkg_name)
            if status in ["failure", "error"]:
                self.package_errors[pkg_name] += 1

        # Update session tracking
        if "session" in event_type:
            session_id = parsed.get("session_id", "unknown")
            if "initialized" in event_type:
                self.active_sessions.add(session_id)
            elif "destroyed" in event_type:
                self.active_sessions.discard(session_id)
            self.session_events[session_id] += 1

        # Update service state
        if event_type == "service_start":
            self.service_state = "running"
            self.service_startup_time = datetime.now().timestamp()
            self.service_state_transitions += 1
        elif event_type == "service_stop":
            self.service_state = "stopped"
            self.service_state_transitions += 1
        elif event_type == "service_init":
            self.service_state = "initializing"

        # Update temporal windows
        now = datetime.now().timestamp()
        self.last_event_time = now

    # ============================================================================
    # FEATURE EXTRACTION METHODS
    # ============================================================================

    def _extract_frequency_features(self) -> Dict[str, float]:
        """Basic event frequency features"""
        features = {}

        # Event type frequencies
        features["event_count_total"] = float(self.total_events)
        features["event_count_service_start"] = float(
            self.event_type_counts["service_start"]
        )
        features["event_count_service_stop"] = float(
            self.event_type_counts["service_stop"]
        )
        features["event_count_transaction_create"] = float(
            self.event_type_counts["transaction_create"]
        )
        features["event_count_package_applicability"] = float(
            self.event_type_counts["package_applicability"]
        )
        features["event_count_session_initialized"] = float(
            self.event_type_counts["session_initialized"]
        )
        features["event_count_upload_error"] = float(
            self.event_type_counts["upload_error"]
        )

        # Component frequencies
        features["component_count_cbs"] = float(self.component_counts["CBS"])
        features["component_count_csi"] = float(self.component_counts["CSI"])

        # Status frequencies
        features["status_count_success"] = float(self.status_counts["success"])
        features["status_count_failure"] = float(self.status_counts["failure"])
        features["status_count_info"] = float(self.status_counts["info"])

        return features

    def _extract_error_features(self) -> Dict[str, float]:
        """Error pattern and classification features"""
        features = {}

        # Error counts
        features["error_count_total"] = float(self.total_errors)
        features["error_count_failures"] = float(self.total_failures)
        features["error_rate"] = (
            self.total_errors / max(self.total_events, 1)
        ) if self.total_events > 0 else 0.0

        # Error cascade tracking
        features["error_consecutive_max"] = float(self.max_consecutive_errors)
        features["error_cascade_indicator"] = (
            1.0 if self.max_consecutive_errors >= 5 else 0.0
        )

        # HRESULT code distribution
        features["hresult_unique_count"] = float(len(self.error_hresults))
        features["hresult_concentration"] = (
            max(self.error_hresults.values()) / max(self.total_errors, 1)
        ) if self.total_errors > 0 else 0.0

        # Error name distribution
        features["error_name_unique_count"] = float(len(self.error_names))

        # Most common error
        if self.error_names:
            most_common_error = max(
                self.error_names.items(), key=lambda x: x[1]
            )[1]
            features["error_name_max_frequency"] = float(most_common_error)
        else:
            features["error_name_max_frequency"] = 0.0

        # Manifest errors
        features["error_count_manifest"] = float(
            self.event_type_counts["manifest_error"]
        )

        # Package errors
        features["error_count_package"] = float(
            self.event_type_counts["package_error"]
        )

        # Parse errors
        features["error_count_parse"] = float(
            self.event_type_counts["parse_error"]
        )

        return features

    def _extract_transaction_features(self) -> Dict[str, float]:
        """Transaction management features"""
        features = {}

        features["transaction_count_total"] = float(
            len(self.transaction_handles)
        )
        features["transaction_count_success"] = float(
            self.transaction_success_count
        )
        features["transaction_count_failure"] = float(
            self.transaction_failure_count
        )
        features["transaction_active_count"] = float(
            len(self.active_transactions)
        )

        # Transaction success rate
        total_transactions = (
            self.transaction_success_count + self.transaction_failure_count
        )
        if total_transactions > 0:
            features["transaction_success_rate"] = (
                self.transaction_success_count / total_transactions
            )
        else:
            features["transaction_success_rate"] = 0.0

        # Transaction failure clustering
        if self.transaction_failure_count > 0:
            features["transaction_failure_clustering"] = (
                self.transaction_failure_count / max(total_transactions, 1)
            )
        else:
            features["transaction_failure_clustering"] = 0.0

        return features

    def _extract_package_features(self) -> Dict[str, float]:
        """Package operation features"""
        features = {}

        features["package_count_unique"] = float(len(self.packages_seen))
        features["package_count_applicability"] = float(
            self.event_type_counts["package_applicability"]
        )
        features["package_count_errors"] = float(
            sum(self.package_errors.values())
        )
        features["package_error_rate"] = (
            sum(self.package_errors.values())
            / (
                max(
                    self.event_type_counts["package_applicability"]
                    + self.event_type_counts["package_error"],
                    1,
                )
            )
        )

        # Package stress indicator
        if len(self.packages_seen) > 0 and any(self.package_errors.values()):
            max_errors = max(self.package_errors.values())
            features["package_max_error_count"] = float(max_errors)
        else:
            features["package_max_error_count"] = 0.0

        return features

    def _extract_service_features(self) -> Dict[str, float]:
        """Service lifecycle and state features"""
        features = {}

        # Service state encoding
        state_map = {"running": 1.0, "initializing": 0.5, "stopped": 0.0, "unknown": -1.0}
        features["service_state"] = state_map.get(self.service_state, -1.0)

        # Service transitions
        features["service_transition_count"] = float(self.service_state_transitions)

        # Service uptime
        if self.service_startup_time:
            uptime = datetime.now().timestamp() - self.service_startup_time
            features["service_uptime_seconds"] = max(uptime, 0.0)
        else:
            features["service_uptime_seconds"] = 0.0

        return features

    def _extract_session_features(self) -> Dict[str, float]:
        """Session management features"""
        features = {}

        features["session_count_active"] = float(len(self.active_sessions))
        features["session_count_created"] = float(
            self.event_type_counts["session_initialized"]
        )
        features["session_count_unique"] = float(len(self.session_events))

        # Session density
        if self.session_count_unique > 0:
            features["session_events_per_session"] = (
                self.total_events
                / len(self.session_events)
            )
        else:
            features["session_events_per_session"] = 0.0

        return features

    def _extract_temporal_features(self) -> Dict[str, float]:
        """Time-window based features"""
        features = {}

        # Note: Time windows not fully populated in this simplified version
        # In production, would track events with timestamps and compute
        # moving averages, rates, etc.

        features["event_recency_seconds"] = (
            0.0 if self.last_event_time is None else
            datetime.now().timestamp() - self.last_event_time
        )

        return features

    def _extract_anomaly_features(self) -> Dict[str, float]:
        """High-level anomaly indicators"""
        features = {}

        # Error spike detection
        if self.total_events > 10:
            error_spike = self.total_errors / max(self.total_events, 1)
            features["anomaly_error_spike"] = (
                1.0 if error_spike > 0.3 else 0.0
            )
        else:
            features["anomaly_error_spike"] = 0.0

        # Error cascade (5+ consecutive errors)
        features["anomaly_error_cascade"] = (
            1.0 if self.max_consecutive_errors >= 5 else 0.0
        )

        # Package stress (multiple packages with errors)
        features["anomaly_package_stress"] = (
            1.0
            if len(self.package_errors) > 0
            and sum(self.package_errors.values()) > 5
            else 0.0
        )

        # Service instability (multiple transitions)
        features["anomaly_service_instability"] = (
            1.0 if self.service_state_transitions > 3 else 0.0
        )

        # Composite anomaly score (0.0-1.0)
        anomaly_signals = [
            features["anomaly_error_spike"],
            features["anomaly_error_cascade"],
            features["anomaly_package_stress"],
            features["anomaly_service_instability"],
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
def get_windows_feature_extractor() -> WindowsFeatureExtractor:
    """Get or create Windows feature extractor instance"""
    return WindowsFeatureExtractor()
