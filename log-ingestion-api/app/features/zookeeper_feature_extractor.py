from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Optional
import numpy as np


class ZookeeperFeatureExtractor:
    """
    Stateful feature extractor for Zookeeper logs.
    Designed for LSTM + anomaly detection + cluster health analytics.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize feature extractor with configurable parameters
        
        Args:
            config: Configuration dictionary with thresholds and window sizes
        """
        self.config = config or {}
        
        # Time windows (in seconds)
        self.windows = {
            'short': self.config.get('window_short', 60),      # 1 minute
            'medium': self.config.get('window_medium', 300),   # 5 minutes
            'long': self.config.get('window_long', 3600),      # 1 hour
            'very_long': self.config.get('window_very_long', 86400),  # 24 hours
        }
        
        # Thresholds for anomaly detection
        self.thresholds = {
            'connection_failure_rate': self.config.get('connection_failure_threshold', 10),
            'session_expiry_rate': self.config.get('session_expiry_threshold', 5),
            'election_duration': self.config.get('election_duration_threshold', 5000),
            'notification_timeout_rate': self.config.get('notification_timeout_threshold', 3),
            'connection_broken_rate': self.config.get('connection_broken_threshold', 5),
            'worker_termination_rate': self.config.get('worker_termination_threshold', 10),
        }
        
        # ===== Session Tracking =====
        self.active_sessions = {}  # session_id -> start_time
        self.session_history = defaultdict(lambda: deque(maxlen=1000))
        self.session_terminations = deque(maxlen=1000)
        self.session_expirations = deque(maxlen=1000)
        
        # ===== Connection Tracking =====
        self.connection_attempts = defaultdict(lambda: deque(maxlen=1000))
        self.connection_failures = defaultdict(lambda: deque(maxlen=1000))
        self.connection_successes = defaultdict(lambda: deque(maxlen=1000))
        self.connection_closures = defaultdict(lambda: deque(maxlen=1000))
        
        # ===== Peer/Node Tracking =====
        self.peer_connections = defaultdict(lambda: defaultdict(lambda: deque(maxlen=1000)))
        self.peer_failures = defaultdict(lambda: deque(maxlen=1000))
        self.quorum_members = set()
        self.leader_elections = deque(maxlen=100)
        
        # ===== Election Tracking =====
        self.election_durations = deque(maxlen=100)
        self.election_timeouts = deque(maxlen=100)
        self.notification_timeouts = deque(maxlen=100)
        
        # ===== Worker Thread Tracking =====
        self.send_worker_terminations = deque(maxlen=1000)
        self.recv_worker_interruptions = deque(maxlen=1000)
        self.worker_interruptions = deque(maxlen=1000)
        
        # ===== System State Tracking =====
        self.looking_state_events = deque(maxlen=100)
        self.following_state_events = deque(maxlen=100)
        self.state_transitions = deque(maxlen=500)
        
        # ===== Network Anomalies =====
        self.connection_broken_events = deque(maxlen=1000)
        self.end_of_stream_events = deque(maxlen=1000)
        self.channel_errors = deque(maxlen=1000)
        
        # ===== Temporal Patterns =====
        self.hourly_events = defaultdict(list)
        self.daily_patterns = defaultdict(list)
        
        # ===== Statistical Baseline =====
        self.baseline = {
            'avg_session_duration': 3600,  # 1 hour
            'std_session_duration': 1800,
            'avg_connections_per_minute': 10,
            'std_connections_per_minute': 5,
            'avg_election_duration': 200,
            'std_election_duration': 100,
            'avg_worker_terminations_per_hour': 5,
            'std_worker_terminations_per_hour': 3,
        }
        
        # ===== Current State =====
        self.current_state = "UNKNOWN"  # LOOKING, FOLLOWING, LEADING
        self.current_leader = None
        self.my_id = None
        
    def extract(self, log) -> Dict:
        """
        Extract comprehensive features from a parsed Zookeeper log entry
        
        Args:
            log: Log entry with metadata and parsed content
            
        Returns:
            Dictionary of extracted features for ML model
        """
        parsed = log.metadata.get("parsed", {})
        event_type = parsed.get("event_type", "other")
        timestamp = log.timestamp
        
        # Base features dictionary
        features = {
            "timestamp": timestamp.isoformat(),
            "timestamp_unix": timestamp.timestamp(),
            "hour": timestamp.hour,
            "day_of_week": timestamp.weekday(),
            "is_weekend": 1 if timestamp.weekday() >= 5 else 0,
            "is_business_hours": 1 if 9 <= timestamp.hour <= 17 else 0,
            "is_night_hours": 1 if timestamp.hour < 6 or timestamp.hour > 22 else 0,
        }
        
        # Add event-specific features
        if "quorum" in event_type or "election" in event_type or "fle" in event_type:
            self._extract_quorum_features(log, parsed, timestamp, features)
        elif "zkserver" in event_type or "session" in event_type:
            self._extract_session_features(log, parsed, timestamp, features)
        elif "nioserver" in event_type or "connection" in event_type:
            self._extract_connection_features(log, parsed, timestamp, features)
        elif "learner" in event_type:
            self._extract_learner_features(log, parsed, timestamp, features)
        else:
            self._extract_other_features(log, parsed, timestamp, features)
        
        # Add temporal features
        self._add_temporal_features(timestamp, features)
        
        # Add anomaly scores
        self._calculate_anomaly_scores(features, event_type)
        
        # Calculate risk score
        features["risk_score"] = self._calculate_risk_score(features)
        
        # Add event type encoding for LSTM
        features["event_type_code"] = self._encode_event_type(event_type)
        
        # Add level encoding
        level = parsed.get("level", "INFO")
        level_encoding = {"INFO": 1, "WARN": 2, "ERROR": 3, "FATAL": 4}
        features["level_code"] = level_encoding.get(level, 0)
        
        return features
    
    def _extract_quorum_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from quorum and leader election events"""
        event_type = parsed.get("event_type")
        
        # Track leader election
        if event_type == "quorum_new_election":
            self.leader_elections.append(timestamp)
            features["election_started"] = 1
            features["my_id"] = parsed.get("my_id")
            self.my_id = parsed.get("my_id")
        else:
            features["election_started"] = 0
        
        # Track election completion
        if event_type == "quorum_following_election":
            if parsed.get("duration"):
                try:
                    duration = int(parsed.get("duration", 0))
                    self.election_durations.append(duration)
                    features["election_duration"] = duration
                    
                    # Detect abnormal election duration
                    features["election_abnormal"] = 1 if duration > self.thresholds['election_duration'] else 0
                except ValueError:
                    features["election_duration"] = 0
                    features["election_abnormal"] = 0
            else:
                features["election_duration"] = 0
                features["election_abnormal"] = 0
        else:
            features["election_duration"] = 0
            features["election_abnormal"] = 0
        
        # Track state changes
        if event_type == "quorum_looking":
            self.current_state = "LOOKING"
            self.looking_state_events.append(timestamp)
            features["state_looking"] = 1
            features["state_following"] = 0
        elif event_type == "quorum_following" or event_type == "quorum_following_election":
            self.current_state = "FOLLOWING"
            self.following_state_events.append(timestamp)
            features["state_looking"] = 0
            features["state_following"] = 1
        else:
            features["state_looking"] = 0
            features["state_following"] = 0
        
        # Track notification timeouts
        if event_type == "quorum_notification_timeout":
            self.notification_timeouts.append(timestamp)
            features["notification_timeout"] = 1
            features["notification_timeout_count_5min"] = len([
                t for t in self.notification_timeouts 
                if t > timestamp - timedelta(seconds=self.windows['medium'])
            ])
        else:
            features["notification_timeout"] = 0
            features["notification_timeout_count_5min"] = 0
        
        # Track FLE notifications
        if event_type == "fle_notification":
            features["fle_notification"] = 1
            features["notification_leader"] = parsed.get("leader")
            features["notification_sid"] = parsed.get("sid")
            
            # Track if we received notification from non-leader during looking
            if self.current_state == "LOOKING" and parsed.get("n_state") == "LEADING":
                features["notification_from_leader"] = 1
            else:
                features["notification_from_leader"] = 0
        else:
            features["fle_notification"] = 0
            features["notification_from_leader"] = 0
        
        # Track quorum snapshot operations
        if event_type == "quorum_snapshotting":
            features["snapshot_operation"] = 1
            features["snapshot_zxid"] = parsed.get("zxid")
        elif event_type == "quorum_reading_snapshot":
            features["snapshot_operation"] = 1
            features["reading_snapshot"] = 1
        else:
            features["snapshot_operation"] = 0
            features["reading_snapshot"] = 0
        
        # Track quorum connection issues
        if event_type == "quorum_cannot_open_channel":
            peer_id = parsed.get("peer_id")
            self.peer_failures[peer_id].append(timestamp)
            features["quorum_channel_failure"] = 1
            features["peer_failure_count_5min"] = len([
                t for t in self.peer_failures[peer_id] 
                if t > timestamp - timedelta(seconds=self.windows['medium'])
            ])
        else:
            features["quorum_channel_failure"] = 0
            features["peer_failure_count_5min"] = 0
        
        # Track quorum connection broken
        if event_type == "quorum_connection_broken":
            self.connection_broken_events.append(timestamp)
            features["quorum_connection_broken"] = 1
            features["connection_broken_count_5min"] = len([
                t for t in self.connection_broken_events 
                if t > timestamp - timedelta(seconds=self.windows['medium'])
            ])
        else:
            features["quorum_connection_broken"] = 0
            features["connection_broken_count_5min"] = 0
        
        # Track worker terminations
        if event_type == "quorum_send_worker_leaving":
            self.send_worker_terminations.append(timestamp)
            features["send_worker_terminated"] = 1
            features["worker_terminations_5min"] = len([
                t for t in self.send_worker_terminations 
                if t > timestamp - timedelta(seconds=self.windows['medium'])
            ])
        else:
            features["send_worker_terminated"] = 0
            features["worker_terminations_5min"] = 0
        
        # Track worker interruptions
        if event_type == "quorum_interrupted_waiting":
            self.worker_interruptions.append(timestamp)
            features["worker_interrupted"] = 1
            features["worker_interruptions_5min"] = len([
                t for t in self.worker_interruptions 
                if t > timestamp - timedelta(seconds=self.windows['medium'])
            ])
        else:
            features["worker_interrupted"] = 0
            features["worker_interruptions_5min"] = 0
        
        # Track quorum have supporters
        if event_type == "quorum_have_supporters":
            features["quorum_established"] = 1
            features["last_processed_zxid"] = parsed.get("zxid")
        else:
            features["quorum_established"] = 0
    
    def _extract_session_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from session management events"""
        event_type = parsed.get("event_type")
        
        # Track session establishment
        if event_type == "zkserver_established_session":
            session_id = parsed.get("session")
            timeout = parsed.get("timeout", "0")
            
            self.active_sessions[session_id] = {
                'start_time': timestamp,
                'timeout': int(timeout) if timeout else 10000
            }
            self.session_history[session_id].append(timestamp)
            
            features["session_established"] = 1
            features["session_timeout"] = int(timeout) if timeout else 0
            features["active_sessions"] = len(self.active_sessions)
        else:
            features["session_established"] = 0
            features["session_timeout"] = 0
        
        # Track session termination
        if event_type == "zkserver_session_termination":
            session_id = parsed.get("session")
            if session_id in self.active_sessions:
                duration = (timestamp - self.active_sessions[session_id]['start_time']).total_seconds()
                features["session_duration"] = duration
                features["session_abnormally_short"] = 1 if duration < 60 else 0
                features["session_abnormally_long"] = 1 if duration > 28800 else 0
                del self.active_sessions[session_id]
            else:
                features["session_duration"] = 0
                features["session_abnormally_short"] = 0
                features["session_abnormally_long"] = 0
            
            self.session_terminations.append(timestamp)
            features["session_terminated"] = 1
        else:
            features["session_duration"] = 0
            features["session_abnormally_short"] = 0
            features["session_abnormally_long"] = 0
            features["session_terminated"] = 0
        
        # Track session expiration
        if event_type == "zkserver_expiring_session":
            self.session_expirations.append(timestamp)
            features["session_expired"] = 1
            features["session_expired_count_5min"] = len([
                t for t in self.session_expirations 
                if t > timestamp - timedelta(seconds=self.windows['medium'])
            ])
            
            # Remove expired session if exists
            session_id = parsed.get("session")
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
        else:
            features["session_expired"] = 0
            features["session_expired_count_5min"] = 0
        
        # Track active sessions count
        features["active_sessions"] = len(self.active_sessions)
        
        # Track session attempt (new/renew)
        if event_type == "zkserver_new_session_attempt":
            features["new_session_attempt"] = 1
            features["session_attempt_count_5min"] = len([
                t for t in self.session_history['attempts'] 
                if t > timestamp - timedelta(seconds=self.windows['medium'])
            ])
            self.session_history['attempts'].append(timestamp)
        else:
            features["new_session_attempt"] = 0
            features["session_attempt_count_5min"] = 0
        
        if event_type == "zkserver_renew_session_attempt":
            features["renew_session_attempt"] = 1
        else:
            features["renew_session_attempt"] = 0
        
        # Track old client connections
        if event_type == "zkserver_old_client_connection":
            features["old_client_connection"] = 1
        else:
            features["old_client_connection"] = 0
    
    def _extract_connection_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from network connection events"""
        event_type = parsed.get("event_type")
        
        # Track accepted connections
        if event_type == "nioserver_accepted_connection":
            ip = parsed.get("ip", "unknown")
            self.connection_attempts[ip].append(timestamp)
            features["connection_accepted"] = 1
            
            cutoff_medium = timestamp - timedelta(seconds=self.windows['medium'])
            features["connection_accepted_count_5min"] = len([
                t for t in self.connection_attempts[ip] if t > cutoff_medium
            ])
        else:
            features["connection_accepted"] = 0
            features["connection_accepted_count_5min"] = 0
        
        # Track connection closures
        if event_type == "nioserver_closed_connection_session":
            features["connection_closed_with_session"] = 1
            self.connection_closures['with_session'].append(timestamp)
        elif event_type == "nioserver_closed_connection_no_session":
            features["connection_closed_no_session"] = 1
            self.connection_closures['no_session'].append(timestamp)
        else:
            features["connection_closed_with_session"] = 0
            features["connection_closed_no_session"] = 0
        
        # Track connection failures
        if event_type == "nioserver_end_of_stream":
            self.end_of_stream_events.append(timestamp)
            features["end_of_stream"] = 1
            features["end_of_stream_count_5min"] = len([
                t for t in self.end_of_stream_events 
                if t > timestamp - timedelta(seconds=self.windows['medium'])
            ])
        else:
            features["end_of_stream"] = 0
            features["end_of_stream_count_5min"] = 0
        
        if event_type == "nioserver_exception_close":
            features["exception_close"] = 1
            self.channel_errors.append(timestamp)
        else:
            features["exception_close"] = 0
        
        # Track quorum connections
        if event_type == "quorum_received_connection":
            features["quorum_connection_received"] = 1
            ip = parsed.get("ip", "unknown")
            self.peer_connections[ip]['received'].append(timestamp)
        else:
            features["quorum_connection_received"] = 0
        
        # Calculate connection success/failure ratio
        total_attempts = len(self.connection_attempts.get('total', []))
        total_failures = len(self.end_of_stream_events) + len(self.channel_errors)
        features["connection_success_rate"] = (total_attempts - total_failures) / max(total_attempts, 1)
    
    def _extract_learner_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from learner (follower) events"""
        event_type = parsed.get("event_type")
        
        if event_type == "learner_goodbye":
            features["learner_goodbye"] = 1
            features["disconnected_peer_ip"] = parsed.get("ip")
            self.peer_failures['goodbye'].append(timestamp)
        else:
            features["learner_goodbye"] = 0
        
        if event_type == "learner_unexpected_exception":
            features["learner_unexpected_exception"] = 1
        else:
            features["learner_unexpected_exception"] = 0
        
        if event_type == "learner_follower_sid":
            features["follower_info"] = 1
            features["follower_sid"] = parsed.get("sid")
            self.quorum_members.add(parsed.get("sid"))
        else:
            features["follower_info"] = 0
        
        features["quorum_members_count"] = len(self.quorum_members)
    
    def _extract_other_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from other event types"""
        event_type = parsed.get("event_type")
        
        # Track environment info
        if event_type == "environment_info":
            features["environment_event"] = 1
            features["env_key"] = parsed.get("env_key", "")
            features["env_value"] = parsed.get("env_value", "")
        else:
            features["environment_event"] = 0
        
        # Track configuration changes
        if event_type in ["config_tick_time", "config_min_session_timeout", "config_max_session_timeout"]:
            features["config_change"] = 1
            if event_type == "config_tick_time":
                features["tick_time"] = parsed.get("tick_time", 0)
            elif event_type == "config_min_session_timeout":
                features["min_session_timeout"] = parsed.get("timeout", 0)
            elif event_type == "config_max_session_timeout":
                features["max_session_timeout"] = parsed.get("timeout", 0)
        else:
            features["config_change"] = 0
        
        # Track auto purge settings
        if event_type == "config_autopurge_snap":
            features["autopurge_snap_count"] = parsed.get("snap_retain_count", 0)
        elif event_type == "config_autopurge_interval":
            features["autopurge_interval"] = parsed.get("purge_interval", 0)
        
        # Track keeper exceptions
        if event_type == "keeper_exception":
            features["keeper_exception"] = 1
            features["keeper_error_path"] = parsed.get("error_path", "")
        else:
            features["keeper_exception"] = 0
        
        # Track shutdown events
        if event_type == "shutdown_complete":
            features["shutdown_complete"] = 1
        elif event_type == "starting_quorum_peer":
            features["starting_quorum"] = 1
        else:
            features["shutdown_complete"] = 0
            features["starting_quorum"] = 0
    
    def _add_temporal_features(self, timestamp: datetime, features: Dict):
        """Add time-based aggregate features"""
        hour = timestamp.hour
        
        # Track hourly events
        self.hourly_events[hour].append(timestamp)
        
        # Clean old entries (keep last 7 days)
        cutoff = timestamp - timedelta(days=7)
        for h in list(self.hourly_events.keys()):
            self.hourly_events[h] = [t for t in self.hourly_events[h] if t > cutoff]
        
        # Calculate activity ratio for current hour
        if self.hourly_events[hour]:
            features["hour_activity"] = len(self.hourly_events[hour])
            
            # Compare to average of other hours
            other_hours_activity = []
            for h, events in self.hourly_events.items():
                if h != hour and events:
                    other_hours_activity.append(len(events))
            
            if other_hours_activity:
                avg_other_hours = np.mean(other_hours_activity)
                features["hour_activity_ratio"] = features["hour_activity"] / avg_other_hours if avg_other_hours > 0 else 1
            else:
                features["hour_activity_ratio"] = 1
        else:
            features["hour_activity"] = 0
            features["hour_activity_ratio"] = 1
        
        # Day of week patterns
        dow = timestamp.weekday()
        self.daily_patterns[dow].append(timestamp)
        cutoff_weekly = timestamp - timedelta(days=30)
        self.daily_patterns[dow] = [t for t in self.daily_patterns[dow] if t > cutoff_weekly]
        
        features["dow_activity"] = len(self.daily_patterns[dow])
    
    def _calculate_anomaly_scores(self, features: Dict, event_type: str):
        """Calculate anomaly scores for ML model"""
        anomaly_score = 0.0
        
        # Election duration anomaly
        if features.get("election_duration", 0) > 0:
            deviation = abs(features["election_duration"] - self.baseline['avg_election_duration']) / (self.baseline['std_election_duration'] + 1)
            anomaly_score += min(deviation * 0.2, 0.4)
        
        # Session expiration anomaly
        if features.get("session_expired_count_5min", 0) > self.thresholds['session_expiry_rate']:
            anomaly_score += min(features["session_expired_count_5min"] * 0.05, 0.3)
        
        # Connection failure anomaly
        if features.get("end_of_stream_count_5min", 0) > self.thresholds['connection_failure_rate']:
            anomaly_score += min(features["end_of_stream_count_5min"] * 0.03, 0.3)
        
        # Connection broken anomaly
        if features.get("connection_broken_count_5min", 0) > self.thresholds['connection_broken_rate']:
            anomaly_score += min(features["connection_broken_count_5min"] * 0.04, 0.3)
        
        # Worker termination anomaly
        if features.get("worker_terminations_5min", 0) > self.thresholds['worker_termination_rate']:
            anomaly_score += min(features["worker_terminations_5min"] * 0.02, 0.2)
        
        # Notification timeout anomaly
        if features.get("notification_timeout_count_5min", 0) > self.thresholds['notification_timeout_rate']:
            anomaly_score += min(features["notification_timeout_count_5min"] * 0.1, 0.5)
        
        # Quorum connection failure
        if features.get("peer_failure_count_5min", 0) > 3:
            anomaly_score += min(features["peer_failure_count_5min"] * 0.05, 0.3)
        
        # Session duration anomaly
        if features.get("session_duration", 0) > 0:
            deviation = abs(features["session_duration"] - self.baseline['avg_session_duration']) / (self.baseline['std_session_duration'] + 1)
            anomaly_score += min(deviation * 0.1, 0.2)
        
        # Keeper exception anomaly
        if features.get("keeper_exception", 0):
            anomaly_score += 0.2
        
        features["anomaly_score"] = min(anomaly_score, 1.0)
    
    def _calculate_risk_score(self, features: Dict) -> int:
        """
        Calculate comprehensive risk score (0-100)
        
        Higher score indicates higher risk/priority
        """
        risk_score = 0
        
        # Election issues (up to 25 points)
        if features.get("election_duration", 0) > self.thresholds['election_duration']:
            risk_score += min(features["election_duration"] / 100, 15)
        if features.get("notification_timeout_count_5min", 0) > 0:
            risk_score += min(features["notification_timeout_count_5min"] * 5, 10)
        
        # Session issues (up to 20 points)
        risk_score += min(features.get("session_expired_count_5min", 0) * 4, 15)
        risk_score += min(features.get("session_abnormally_short", 0) * 5, 5)
        
        # Connection issues (up to 25 points)
        risk_score += min(features.get("end_of_stream_count_5min", 0) * 3, 10)
        risk_score += min(features.get("connection_broken_count_5min", 0) * 4, 10)
        risk_score += min(features.get("connection_accepted_count_5min", 0) * 1, 5)
        
        # Worker issues (up to 15 points)
        risk_score += min(features.get("worker_terminations_5min", 0) * 2, 10)
        risk_score += min(features.get("worker_interruptions_5min", 0) * 2, 5)
        
        # Quorum issues (up to 15 points)
        risk_score += min(features.get("peer_failure_count_5min", 0) * 3, 10)
        risk_score += min(features.get("quorum_channel_failure", 0) * 5, 5)
        
        # Keeper exceptions (up to 10 points)
        if features.get("keeper_exception", 0):
            risk_score += 10
        
        # Connection success rate impact
        if features.get("connection_success_rate", 1) < 0.5:
            risk_score += 15
        
        # Add anomaly score contribution
        risk_score += features.get("anomaly_score", 0) * 20
        
        return min(risk_score, 100)
    
    def _encode_event_type(self, event_type: str) -> int:
        """Encode event type for LSTM model"""
        event_encoding = {
            # Quorum events (1-15)
            "quorum_notification_timeout": 1,
            "quorum_new_election": 2,
            "quorum_following": 3,
            "quorum_following_election": 4,
            "quorum_looking": 5,
            "quorum_getting_snapshot": 6,
            "quorum_sending_diff": 7,
            "quorum_snapshotting": 8,
            "quorum_reading_snapshot": 9,
            "quorum_have_supporters": 10,
            "quorum_first_is": 11,
            
            # Connection manager events (16-25)
            "quorum_received_connection": 16,
            "quorum_cannot_open_channel": 17,
            "quorum_smaller_server_id": 18,
            "quorum_election_bind_port": 19,
            "quorum_send_worker_leaving": 20,
            "quorum_interrupted_waiting": 21,
            "quorum_interrupting_send_worker": 22,
            "quorum_connection_broken": 23,
            
            # Learner events (26-30)
            "learner_goodbye": 26,
            "learner_unexpected_exception": 27,
            "learner_follower_sid": 28,
            
            # NIOServer events (31-40)
            "nioserver_accepted_connection": 31,
            "nioserver_closed_connection_session": 32,
            "nioserver_closed_connection_no_session": 33,
            "nioserver_end_of_stream": 34,
            "nioserver_exception_close": 35,
            
            # ZooKeeper Server events (41-50)
            "zkserver_new_session_attempt": 41,
            "zkserver_renew_session_attempt": 42,
            "zkserver_established_session": 43,
            "zkserver_expiring_session": 44,
            "zkserver_session_termination": 45,
            "zkserver_revalidating_client": 46,
            "zkserver_old_client_connection": 47,
            
            # FLE events (51-55)
            "fle_notification": 51,
            
            # Configuration events (56-60)
            "environment_info": 56,
            "config_tick_time": 57,
            "config_min_session_timeout": 58,
            "config_max_session_timeout": 59,
            "config_autopurge_snap": 60,
            "config_autopurge_interval": 61,
            
            # Exception events (62-65)
            "keeper_exception": 62,
            "shutdown_complete": 63,
            "starting_quorum_peer": 64,
            
            "other": 0
        }
        return event_encoding.get(event_type, 0)
    
    def get_cluster_health_report(self) -> Dict:
        """
        Generate comprehensive Zookeeper cluster health report
        
        Returns:
            Dictionary with health metrics and recommendations
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "quorum_health": {},
            "session_health": {},
            "connection_health": {},
            "worker_health": {},
            "recommendations": []
        }
        
        # Quorum health
        report["quorum_health"]["election_count"] = len(self.leader_elections)
        report["quorum_health"]["election_durations"] = list(self.election_durations)[-10:] if self.election_durations else []
        report["quorum_health"]["notification_timeouts"] = len(self.notification_timeouts)
        report["quorum_health"]["quorum_members"] = list(self.quorum_members)
        report["quorum_health"]["current_state"] = self.current_state
        
        # Session health
        report["session_health"]["active_sessions"] = len(self.active_sessions)
        report["session_health"]["terminated_sessions"] = len(self.session_terminations)
        report["session_health"]["expired_sessions"] = len(self.session_expirations)
        report["session_health"]["expiry_rate"] = len(self.session_expirations) / max(len(self.session_history.get('attempts', [])), 1)
        
        # Connection health
        report["connection_health"]["total_connections"] = sum(len(attempts) for attempts in self.connection_attempts.values())
        report["connection_health"]["end_of_stream_errors"] = len(self.end_of_stream_events)
        report["connection_health"]["channel_errors"] = len(self.channel_errors)
        report["connection_health"]["connection_broken"] = len(self.connection_broken_events)
        
        # Worker health
        report["worker_health"]["send_worker_terminations"] = len(self.send_worker_terminations)
        report["worker_health"]["worker_interruptions"] = len(self.worker_interruptions)
        
        # Recommendations
        if len(self.leader_elections) > 5:
            report["recommendations"].append("Multiple leader elections detected. Check network stability and node health.")
        
        if len(self.session_expirations) > 100:
            report["recommendations"].append("High session expiration rate. Consider increasing session timeout or checking client health.")
        
        if len(self.end_of_stream_events) > 50:
            report["recommendations"].append("High number of end-of-stream errors. Investigate network connectivity issues.")
        
        if len(self.notification_timeouts) > 10:
            report["recommendations"].append("Notification timeouts detected. Check quorum communication latency.")
        
        if len(self.send_worker_terminations) > 100:
            report["recommendations"].append("Frequent send worker terminations. Review thread pool configuration and system resources.")
        
        if self.current_state == "LOOKING":
            report["recommendations"].append("Zookeeper is in LOOKING state (leader election in progress). Check if this persists.")
        
        return report
