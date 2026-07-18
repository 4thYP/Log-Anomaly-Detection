"""
HPC Feature Extractor - Fixed-length feature vector generation

This extractor produces behavioral and temporal features from HPC parsed logs.

FEATURE SCHEMA (13 features, all [0,1] normalized):
=================================================
 0. event_rate_5min         - Frequency of events in 5-min window
 1. error_rate              - Fraction of events that are errors (ERROR group)
 2. service_action_rate     - Frequency of SERVICE group actions
 3. system_state_rate       - Frequency of SYSTEM group events
 4. hardware_failure_ratio  - Ratio of unavailable/critical to total hw events
 5. component_diversity     - Unique component count (normalized by max)
 6. node_activity_level     - Nodes with recent activity (normalized)
 7. boot_action_frequency   - Boot-like events in window
 8. halt_action_frequency   - Halt-like events in window
 9. command_id_entropy      - Uniqueness of command IDs (higher = more varied)
10. temporal_concentration  - Distribution of events across time window (higher = clustered)
11. unavailable_count_norm  - Normalized count of unavailable component events
12. error_event_density     - Error events per hour equivalent

All values normalized to [0, 1] using running statistics.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.models.log_models import LogInternal
from app.parsers.log_event_schema import EventGroup
import math


class HPCFeatureExtractor:
    """
    Stateful feature extractor for HPC cluster logs.
    
    Maintains per-server state (identified by log_internal.sid).
    """
    
    # Feature schema (names and ordering)
    FEATURE_SCHEMA = [
        "event_rate_5min",
        "error_rate",
        "service_action_rate",
        "system_state_rate",
        "hardware_failure_ratio",
        "component_diversity",
        "node_activity_level",
        "boot_action_frequency",
        "halt_action_frequency",
        "command_id_entropy",
        "temporal_concentration",
        "unavailable_count_norm",
        "error_event_density",
    ]
    
    def __init__(self):
        # Per-server state tracking: Dict[sid → ServerState]
        self.server_states: Dict[str, 'ServerState'] = defaultdict(lambda: ServerState())

    def extract(self, log_internal: LogInternal) -> List[float]:
        """
        Extract fixed-length feature vector from parsed HPC log.
        
        Args:
            log_internal: Processed log with metadata["parsed"] containing ParsedLogEvent
            
        Returns:
            List of 13 floats, all normalized to [0, 1]
        """
        sid = log_internal.sid
        state = self.server_states[sid]
        
        # Extract timestamp (from parsed log)
        timestamp = self._extract_timestamp(log_internal)
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Retrieve parsed event
        parsed = log_internal.metadata.get("parsed", {})
        event_type = parsed.get("event_type", "unknown")
        event_group = parsed.get("event_group", "system")
        metadata = parsed.get("metadata", {})
        
        # Update state
        state.add_event(
            timestamp=timestamp,
            event_type=event_type,
            event_group=event_group,
            metadata=metadata
        )
        
        # Compute features
        features = [
            state.compute_event_rate_5min(),
            state.compute_error_rate(),
            state.compute_service_action_rate(),
            state.compute_system_state_rate(),
            state.compute_hardware_failure_ratio(),
            state.compute_component_diversity(),
            state.compute_node_activity_level(),
            state.compute_boot_frequency(),
            state.compute_halt_frequency(),
            state.compute_command_id_entropy(),
            state.compute_temporal_concentration(timestamp),
            state.compute_unavailable_count_norm(),
            state.compute_error_event_density(timestamp),
        ]
        
        # Ensure all features are in [0, 1]
        features = [max(0.0, min(1.0, f)) for f in features]
        
        return features

    def _extract_timestamp(self, log_internal: LogInternal) -> Optional[datetime]:
        """Extract ISO 8601 timestamp from parsed log and convert to datetime."""
        try:
            parsed = log_internal.metadata.get("parsed", {})
            timestamp_str = parsed.get("timestamp")
            
            if timestamp_str:
                # Parse ISO 8601 format
                # Handle both "2004-02-26T10:39:02" and "2015-07-29T19:04:12.394"
                if "." in timestamp_str:
                    return datetime.fromisoformat(timestamp_str)
                else:
                    return datetime.fromisoformat(timestamp_str)
            
            return None
        except Exception:
            return None


class ServerState:
    """
    Maintains stateful information for a single HPC server (identified by sid).
    """
    
    def __init__(self, window_seconds=300):
        """Initialize with 5-minute window (300 seconds)."""
        self.window_seconds = window_seconds
        
        # Event history: List[(timestamp, event_type, event_group, metadata)]
        self.events: List[tuple] = []
        
        # Aggregates (updated as events arrive)
        self.event_counts = defaultdict(int)  # event_type → count
        self.group_counts = defaultdict(int)  # event_group → count
        self.component_names = set()          # Unique component identifiers
        self.node_ids = set()                 # Unique nodes
        self.command_ids = []                 # Command IDs seen
        self.unavailable_count = 0            # Lifetime count of unavailable events
        
        # Normalization helpers
        self.max_components_seen = 1
        self.max_nodes_seen = 1
        self.max_event_rate_seen = 1.0

    def add_event(self, timestamp: datetime, event_type: str, event_group: str, metadata: Dict):
        """Record an event and update aggregates."""
        self.events.append((timestamp, event_type, event_group, metadata))
        
        # Update counters
        self.event_counts[event_type] += 1
        self.group_counts[event_group] += 1
        
        # Track entities
        if "component_name" in metadata:
            self.component_names.add(metadata["component_name"])
            self.max_components_seen = max(self.max_components_seen, len(self.component_names))
        
        if "node" in metadata:
            self.node_ids.add(metadata["node"])
            self.max_nodes_seen = max(self.max_nodes_seen, len(self.node_ids))
        
        if "command_id" in metadata:
            self.command_ids.append(int(metadata["command_id"]))
        
        # Track unavailable events (for alert aggregation)
        if event_type == "component_unavailable":
            self.unavailable_count += 1
        
        # Cleanup old events (keep ~1 hour window for lookback)
        cutoff = timestamp - timedelta(seconds=3600)
        self.events = [(ts, et, eg, md) for ts, et, eg, md in self.events if ts >= cutoff]

    def get_window_events(self, current_time: datetime) -> List[tuple]:
        """Get events from last 5-min window."""
        cutoff = current_time - timedelta(seconds=self.window_seconds)
        return [(ts, et, eg, md) for ts, et, eg, md in self.events if ts >= cutoff]

    def compute_event_rate_5min(self) -> float:
        """
        Event frequency in 5-min window.
        Normalized: rate / (max rate ever seen)
        """
        if not self.events:
            return 0.0
        
        current_time = self.events[-1][0]  # Last event time
        window_events = self.get_window_events(current_time)
        
        # Count events per minute
        rate = len(window_events) / (self.window_seconds / 60.0)
        
        self.max_event_rate_seen = max(self.max_event_rate_seen, rate)
        normalized = rate / max(1.0, self.max_event_rate_seen)
        
        return normalized

    def compute_error_rate(self) -> float:
        """Fraction of events in ERROR group."""
        if not self.events:
            return 0.0
        
        current_time = self.events[-1][0]
        window_events = self.get_window_events(current_time)
        
        if not window_events:
            return 0.0
        
        error_count = sum(1 for _, _, eg, _ in window_events if eg == EventGroup.ERROR)
        return error_count / len(window_events)

    def compute_service_action_rate(self) -> float:
        """Fraction of SERVICE group events in window."""
        if not self.events:
            return 0.0
        
        current_time = self.events[-1][0]
        window_events = self.get_window_events(current_time)
        
        if not window_events:
            return 0.0
        
        service_count = sum(1 for _, _, eg, _ in window_events if eg == EventGroup.SERVICE)
        return service_count / len(window_events)

    def compute_system_state_rate(self) -> float:
        """Fraction of SYSTEM group events in window."""
        if not self.events:
            return 0.0
        
        current_time = self.events[-1][0]
        window_events = self.get_window_events(current_time)
        
        if not window_events:
            return 0.0
        
        system_count = sum(1 for _, _, eg, _ in window_events if eg == EventGroup.SYSTEM)
        return system_count / len(window_events)

    def compute_hardware_failure_ratio(self) -> float:
        """
        Ratio of hardware failures (unavailable, critical) to total hardware events.
        """
        failure_types = {"component_unavailable", "component_critical", "component_blocked"}
        
        if not self.events:
            return 0.0
        
        current_time = self.events[-1][0]
        window_events = self.get_window_events(current_time)
        
        hw_events = [et for _, et, _, _ in window_events if et.startswith("component_")]
        if not hw_events:
            return 0.0
        
        failures = sum(1 for et in hw_events if et in failure_types)
        return failures / len(hw_events)

    def compute_component_diversity(self) -> float:
        """
        Unique component count, normalized by max ever seen.
        """
        if self.max_components_seen <= 1:
            return 0.0
        
        current_count = len(self.component_names)
        return min(1.0, current_count / max(1, self.max_components_seen))

    def compute_node_activity_level(self) -> float:
        """
        Count of active nodes in window, normalized by max ever seen.
        """
        if not self.events:
            return 0.0
        
        current_time = self.events[-1][0]
        window_events = self.get_window_events(current_time)
        
        active_nodes = set()
        for _, _, _, md in window_events:
            if "node" in md:
                active_nodes.add(md["node"])
        
        if self.max_nodes_seen <= 1:
            return 0.0
        
        return min(1.0, len(active_nodes) / self.max_nodes_seen)

    def compute_boot_frequency(self) -> float:
        """Frequency of boot-like events (boot, risboot, bootvmunix)."""
        boot_types = {"boot_started", "risboot_started", "bootvmunix_started"}
        
        if not self.events:
            return 0.0
        
        current_time = self.events[-1][0]
        window_events = self.get_window_events(current_time)
        
        if not window_events:
            return 0.0
        
        boot_count = sum(1 for _, et, _, _ in window_events if et in boot_types)
        return min(1.0, boot_count / max(1, len(window_events)))

    def compute_halt_frequency(self) -> float:
        """Frequency of halt events."""
        halt_types = {"halt_started"}
        
        if not self.events:
            return 0.0
        
        current_time = self.events[-1][0]
        window_events = self.get_window_events(current_time)
        
        if not window_events:
            return 0.0
        
        halt_count = sum(1 for _, et, _, _ in window_events if et in halt_types)
        return min(1.0, halt_count / max(1, len(window_events)))

    def compute_command_id_entropy(self) -> float:
        """
        Shannon entropy of command IDs.
        Higher entropy = more varied commands (less repetitive patterns).
        """
        if not self.command_ids or len(self.command_ids) < 2:
            return 0.0
        
        # Count frequency of each command ID
        from collections import Counter
        cmd_counts = Counter(self.command_ids[-100:])  # Last 100 commands
        
        total = len(cmd_counts)
        if total <= 1:
            return 0.0
        
        # Shannon entropy
        entropy = 0.0
        for count in cmd_counts.values():
            if count > 0:
                p = count / len(self.command_ids[-100:])
                entropy -= p * math.log2(p)
        
        # Normalize to [0, 1] (max entropy for n symbols is log2(n))
        max_entropy = math.log2(min(total, len(self.command_ids[-100:])))
        if max_entropy > 0:
            normalized_entropy = entropy / max_entropy
        else:
            normalized_entropy = 0.0
        
        return min(1.0, normalized_entropy)

    def compute_temporal_concentration(self, current_time: datetime) -> float:
        """
        Measure of temporal clustering (0 = spread uniformly, 1 = all clustered).
        Uses the ratio of occupied time slots to total window.
        """
        window_events = self.get_window_events(current_time)
        
        if len(window_events) < 2:
            return 0.0
        
        # Divide window into 10 buckets, count non-empty buckets
        bucket_size = self.window_seconds / 10
        buckets = set()
        
        cutoff = current_time - timedelta(seconds=self.window_seconds)
        for ts, _, _, _ in window_events:
            bucket = int((ts - cutoff).total_seconds() / bucket_size)
            buckets.add(bucket)
        
        # Concentration: 1 - (occupied_buckets / total_buckets)
        # High = clustered, Low = spread
        occupied_fraction = len(buckets) / 10.0
        concentration = 1.0 - occupied_fraction  # Invert for "clustering"
        
        return max(0.0, min(1.0, concentration))

    def compute_unavailable_count_norm(self) -> float:
        """
        Normalized count of unavailable component events (lifetime).
        Uses log scaling to handle large counts.
        """
        if self.unavailable_count == 0:
            return 0.0
        
        # Log scale: log(1 + count) / log(1 + max_expected)
        # Assume max ~100 unavailable events = threshold for "normal"
        log_count = math.log(1 + self.unavailable_count)
        log_max = math.log(1 + 100)  # Threshold at 100
        
        return min(1.0, log_count / log_max)

    def compute_error_event_density(self, current_time: datetime) -> float:
        """
        Error event density (count per hour).
        Normalized against typical rate.
        """
        if not self.events:
            return 0.0
        
        # Look at last hour
        cutoff = current_time - timedelta(hours=1)
        hour_events = [(ts, et, eg, md) for ts, et, eg, md in self.events if ts >= cutoff]
        
        error_count = sum(1 for _, _, eg, _ in hour_events if eg == EventGroup.ERROR)
        
        # Normalize: ~10 errors/hour = normal, >50 = high
        density = error_count / 10.0
        
        return min(1.0, density)
