"""
HealthApp Feature Extractor - Fixed-length feature vector generation

This extractor produces behavioral and temporal features from HealthApp parsed logs.

FEATURE SCHEMA (15 features, all [0,1] normalized):
===================================================
 0. event_rate_5min              - Event frequency in 5-min window
 1. motion_event_density         - Step tracking event frequency
 2. report_frequency             - Health metrics reports per time window
 3. screen_on_ratio              - Fraction of time device is active
 4. step_count_delta             - Change in step count (normalized)
 5. calorie_accumulation_rate    - Calorie burn rate (normalized)
 6. altitude_gain_rate           - Altitude change rate (normalized)
 7. data_sync_rate               - Sync/persistence event frequency
 8. error_event_ratio            - Fraction of events that are errors
 9. component_diversity          - Unique component count (normalized)
10. motion_burst_intensity       - Clustering of motion events
11. step_stand_ratio             - Steps vs stands balance
12. metric_calculation_latency   - Delay between motion and metrics report
13. lifecycle_event_intensity    - Screen on/off frequency
14. persistence_flush_rate       - Data flush frequency

All values normalized to [0, 1] using running statistics.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.models.log_models import LogInternal
from app.parsers.log_event_schema import EventGroup
import math


class HealthAppFeatureExtractor:
    """
    Stateful feature extractor for HealthApp fitness logs.
    
    Maintains per-server state (identified by log_internal.sid).
    """
    
    # Feature schema (names and ordering)
    FEATURE_SCHEMA = [
        "event_rate_5min",
        "motion_event_density",
        "report_frequency",
        "screen_on_ratio",
        "step_count_delta",
        "calorie_accumulation_rate",
        "altitude_gain_rate",
        "data_sync_rate",
        "error_event_ratio",
        "component_diversity",
        "motion_burst_intensity",
        "step_stand_ratio",
        "metric_calculation_latency",
        "lifecycle_event_intensity",
        "persistence_flush_rate",
    ]
    
    def __init__(self):
        # Per-server state tracking: Dict[sid → ServerState]
        self.server_states: Dict[str, 'HealthAppServerState'] = defaultdict(lambda: HealthAppServerState())

    def extract(self, log_internal: LogInternal) -> List[float]:
        """
        Extract fixed-length feature vector from parsed HealthApp log.
        
        Args:
            log_internal: Processed log with metadata["parsed"] containing ParsedLogEvent
            
        Returns:
            List of 15 floats, all normalized to [0, 1]
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
        component = parsed.get("component", "unknown")
        metadata = parsed.get("metadata", {})
        
        # Update state
        state.add_event(
            timestamp=timestamp,
            event_type=event_type,
            event_group=event_group,
            component=component,
            metadata=metadata
        )
        
        # Compute features
        features = [
            state.compute_event_rate_5min(),
            state.compute_motion_event_density(),
            state.compute_report_frequency(),
            state.compute_screen_on_ratio(),
            state.compute_step_count_delta(),
            state.compute_calorie_accumulation_rate(),
            state.compute_altitude_gain_rate(),
            state.compute_data_sync_rate(),
            state.compute_error_event_ratio(),
            state.compute_component_diversity(),
            state.compute_motion_burst_intensity(timestamp),
            state.compute_step_stand_ratio(),
            state.compute_metric_calculation_latency(),
            state.compute_lifecycle_event_intensity(),
            state.compute_persistence_flush_rate(),
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
                # Parse ISO 8601 format or HealthApp format
                # "2017-12-23T22:15:29.606"
                if "T" in timestamp_str:
                    return datetime.fromisoformat(timestamp_str)
                else:
                    return datetime.fromisoformat(timestamp_str)
            
            return None
        except Exception:
            return None


class HealthAppServerState:
    """
    Maintains stateful information for a single HealthApp device (identified by sid).
    """
    
    def __init__(self, window_seconds=300):
        """Initialize with 5-minute window (300 seconds)."""
        self.window_seconds = window_seconds
        
        # Event history: List[(timestamp, event_type, event_group, component, metadata)]
        self.events: List[tuple] = []
        
        # Aggregates (updated as events arrive)
        self.event_counts = defaultdict(int)          # event_type → count
        self.group_counts = defaultdict(int)          # event_group → count
        self.component_counts = defaultdict(int)      # component → count
        self.component_names = set()                  # Unique components
        
        # Motion tracking
        self.last_step_count = 0
        self.total_steps = 0
        self.step_events = []                         # [(timestamp, step_count)]
        
        # Metrics tracking
        self.last_calories = 0
        self.total_calories = 0
        self.last_altitude = 0
        self.total_altitude = 0
        self.metrics_events = []                      # [(timestamp, calories, altitude)]
        
        # Lifecycle tracking
        self.screen_on_count = 0
        self.screen_off_count = 0
        self.screen_events = []                       # [(timestamp, state: "on"/"off")]
        
        # Performance metrics
        self.motion_to_report_delays = []             # Delays between motion and report
        
        # Normalization helpers
        self.max_components_seen = 1
        self.max_event_rate_seen = 1.0
        self.max_step_delta_seen = 10

    def add_event(self, timestamp: datetime, event_type: str, event_group: str, 
                  component: str, metadata: Dict):
        """Record an event and update aggregates."""
        self.events.append((timestamp, event_type, event_group, component, metadata))
        
        # Update counters
        self.event_counts[event_type] += 1
        self.group_counts[event_group] += 1
        self.component_counts[component] += 1
        self.component_names.add(component)
        self.max_components_seen = max(self.max_components_seen, len(self.component_names))
        
        # Track motion events (steps)
        if event_type == "step_count_changed":
            current_step = metadata.get("step_count", 0)
            self.step_events.append((timestamp, current_step))
            step_delta = abs(current_step - self.last_step_count)
            self.max_step_delta_seen = max(self.max_step_delta_seen, step_delta)
            self.last_step_count = current_step
            self.total_steps += step_delta
        
        # Track metrics events
        if event_type == "health_metrics_report":
            calories = metadata.get("calories", 0)
            altitude = metadata.get("altitude", 0)
            steps = metadata.get("steps", 0)
            stands = metadata.get("stands", 0)
            self.metrics_events.append((timestamp, calories, altitude, steps, stands))
            self.last_calories = calories
            self.total_calories = calories
            self.last_altitude = altitude
            self.total_altitude = altitude
            
            # Compute delay from last motion event
            if self.step_events:
                last_motion_time = self.step_events[-1][0]
                delay_ms = (timestamp - last_motion_time).total_seconds() * 1000
                if delay_ms >= 0 and delay_ms <= 10000:  # Valid delays up to 10s
                    self.motion_to_report_delays.append(delay_ms)
        
        # Track lifecycle events
        if event_type in ["screen_on_action", "screen_on_received", "screen_on_action"]:
            self.screen_on_count += 1
            self.screen_events.append((timestamp, "on"))
        elif event_type in ["screen_off_received"]:
            self.screen_off_count += 1
            self.screen_events.append((timestamp, "off"))
        
        # Cleanup old events (keep ~1 hour window for lookback)
        cutoff = timestamp - timedelta(seconds=3600)
        self.events = [(ts, et, eg, c, md) for ts, et, eg, c, md in self.events if ts >= cutoff]

    def get_window_events(self, current_time: datetime) -> List[tuple]:
        """Get events from last 5-min window."""
        cutoff = current_time - timedelta(seconds=self.window_seconds)
        return [(ts, et, eg, c, md) for ts, et, eg, c, md in self.events if ts >= cutoff]

    def compute_event_rate_5min(self) -> float:
        """Event frequency in 5-min window. Normalized by max rate seen."""
        if not self.events:
            return 0.0
        
        current_time = self.events[-1][0]
        window_events = self.get_window_events(current_time)
        
        rate = len(window_events) / (self.window_seconds / 60.0)
        self.max_event_rate_seen = max(self.max_event_rate_seen, rate)
        normalized = rate / max(1.0, self.max_event_rate_seen)
        
        return normalized

    def compute_motion_event_density(self) -> float:
        """Fraction of motion events in window."""
        if not self.events:
            return 0.0
        
        current_time = self.events[-1][0]
        window_events = self.get_window_events(current_time)
        
        if not window_events:
            return 0.0
        
        motion_count = sum(1 for _, et, _, _, _ in window_events 
                          if et in ["step_count_changed", "motion_extended"])
        return motion_count / len(window_events)

    def compute_report_frequency(self) -> float:
        """Frequency of health metrics reports."""
        if not self.events:
            return 0.0
        
        current_time = self.events[-1][0]
        window_events = self.get_window_events(current_time)
        
        if not window_events:
            return 0.0
        
        report_count = sum(1 for _, et, _, _, _ in window_events 
                          if et == "health_metrics_report")
        return min(1.0, report_count / 10.0)  # Max ~10 reports per 5 min

    def compute_screen_on_ratio(self) -> float:
        """Fraction of screen on events vs total screen events."""
        total_screen_events = self.screen_on_count + self.screen_off_count
        
        if total_screen_events == 0:
            return 0.5  # Assume neutral if no screen events
        
        return self.screen_on_count / total_screen_events

    def compute_step_count_delta(self) -> float:
        """Change in step count (normalized by max delta ever seen)."""
        if not self.step_events or len(self.step_events) < 2:
            return 0.0
        
        # Get last two step events
        current_step = self.step_events[-1][1]
        prev_step = self.step_events[-2][1]
        
        delta = abs(current_step - prev_step)
        normalized = delta / max(1, self.max_step_delta_seen)
        
        return min(1.0, normalized)

    def compute_calorie_accumulation_rate(self) -> float:
        """Calorie burn rate per minute (normalized)."""
        if not self.metrics_events or len(self.metrics_events) < 2:
            return 0.0
        
        # Get time span and calorie change
        current_calories = self.metrics_events[-1][1]
        prev_calories = self.metrics_events[-2][1]
        
        time_delta_sec = (self.metrics_events[-1][0] - self.metrics_events[-2][0]).total_seconds()
        
        if time_delta_sec <= 0:
            return 0.0
        
        calorie_per_minute = (current_calories - prev_calories) * 60 / time_delta_sec
        
        # Typical values: ~5 cal/min at moderate activity
        normalized = calorie_per_minute / 100.0  # Cap at 100 cal/min
        
        return min(1.0, normalized)

    def compute_altitude_gain_rate(self) -> float:
        """Altitude change rate (normalized)."""
        if not self.metrics_events or len(self.metrics_events) < 2:
            return 0.0
        
        current_altitude = self.metrics_events[-1][2]
        prev_altitude = self.metrics_events[-2][2]
        
        time_delta_sec = (self.metrics_events[-1][0] - self.metrics_events[-2][0]).total_seconds()
        
        if time_delta_sec <= 0:
            return 0.0
        
        altitude_per_minute = (current_altitude - prev_altitude) * 60 / time_delta_sec
        
        # Typical: ~10 m/min while climbing
        normalized = altitude_per_minute / 50.0
        
        return min(1.0, max(0.0, normalized))

    def compute_data_sync_rate(self) -> float:
        """Fraction of persistence/sync events."""
        if not self.events:
            return 0.0
        
        current_time = self.events[-1][0]
        window_events = self.get_window_events(current_time)
        
        if not window_events:
            return 0.0
        
        sync_events = sum(1 for _, _, eg, _, _ in window_events 
                         if eg in ["persistence", "synchronization"])
        return sync_events / len(window_events)

    def compute_error_event_ratio(self) -> float:
        """Fraction of error events."""
        if not self.events:
            return 0.0
        
        current_time = self.events[-1][0]
        window_events = self.get_window_events(current_time)
        
        if not window_events:
            return 0.0
        
        error_count = sum(1 for _, _, eg, _, _ in window_events if eg == "error")
        return error_count / len(window_events)

    def compute_component_diversity(self) -> float:
        """Unique component count (normalized)."""
        if self.max_components_seen <= 1:
            return 0.0
        
        current_components = len(self.component_names)
        return min(1.0, current_components / self.max_components_seen)

    def compute_motion_burst_intensity(self, current_time: datetime) -> float:
        """
        Measure of motion event clustering.
        (0 = spread out, 1 = highly clustered)
        """
        window_events = self.get_window_events(current_time)
        motion_events = [ts for ts, et, eg, _, _ in window_events 
                        if et in ["step_count_changed", "motion_extended"]]
        
        if len(motion_events) < 2:
            return 0.0
        
        # Divide window into 5 buckets
        bucket_size = self.window_seconds / 5
        buckets = set()
        
        cutoff = current_time - timedelta(seconds=self.window_seconds)
        for ts in motion_events:
            bucket = int((ts - cutoff).total_seconds() / bucket_size)
            buckets.add(bucket)
        
        # Clustering: 1 - (occupied_buckets / total_buckets)
        occupied_fraction = len(buckets) / 5.0
        concentration = 1.0 - occupied_fraction
        
        return max(0.0, min(1.0, concentration))

    def compute_step_stand_ratio(self) -> float:
        """Ratio of steps to stands (from metrics reports)."""
        if not self.metrics_events:
            return 0.5
        
        # Get latest report
        latest_steps = self.metrics_events[-1][3]
        latest_stands = self.metrics_events[-1][4]
        
        total = latest_steps + latest_stands
        if total == 0:
            return 0.5
        
        return latest_steps / total

    def compute_metric_calculation_latency(self) -> float:
        """
        Average delay between motion events and metric report.
        Normalized: 0 = instant, 1 = >5s delay.
        """
        if not self.motion_to_report_delays:
            return 0.0
        
        avg_delay_ms = sum(self.motion_to_report_delays) / len(self.motion_to_report_delays)
        
        # Normalize: 5000ms = max acceptable latency
        normalized = avg_delay_ms / 5000.0
        
        return min(1.0, normalized)

    def compute_lifecycle_event_intensity(self) -> float:
        """Frequency of screen on/off events."""
        if not self.events:
            return 0.0
        
        current_time = self.events[-1][0]
        window_events = self.get_window_events(current_time)
        
        if not window_events:
            return 0.0
        
        lifecycle_count = sum(1 for _, et, _, _, _ in window_events 
                             if et.startswith("screen_"))
        
        # Max ~100 screen toggles per 5 min (very frequent)
        return min(1.0, lifecycle_count / 100.0)

    def compute_persistence_flush_rate(self) -> float:
        """Frequency of data flush events."""
        if not self.events:
            return 0.0
        
        current_time = self.events[-1][0]
        window_events = self.get_window_events(current_time)
        
        if not window_events:
            return 0.0
        
        flush_count = sum(1 for _, et, _, _, _ in window_events 
                         if et in ["sensor_data_flushed", "step_data_updated", 
                                   "step_data_retrieved", "data_persisted"])
        
        # Typical: ~5-10 flushes per 5 min
        return min(1.0, flush_count / 10.0)
