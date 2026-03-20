from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from enum import Enum


class RiskLevel(Enum):
    """Risk levels for security and system health events"""
    CRITICAL = 10
    HIGH = 7
    MEDIUM = 4
    LOW = 2
    INFO = 1
    NONE = 0


class AnomalyType(Enum):
    """Types of anomalies that can be detected"""
    BRUTE_FORCE = "brute_force_attack"
    DICTIONARY_ATTACK = "dictionary_attack"
    DISTRIBUTED_ATTACK = "distributed_attack"
    ANONYMOUS_FTP = "anonymous_ftp_abuse"
    SERVICE_FAILURE = "service_failure"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    SUSPICIOUS_HOUR = "suspicious_hour_activity"
    RAPID_SESSION = "rapid_session_switching"
    IP_REPUTATION = "suspicious_ip_reputation"
    RATE_ANOMALY = "rate_anomaly"


class LinuxFeatureExtractor:
    """
    Industry-grade feature extractor for Linux logs.
    
    Features extracted:
    - Time-based patterns (hour, day, frequency)
    - User behavior analytics
    - IP-based threat intelligence
    - Session characteristics
    - System health metrics
    - Attack pattern detection
    - Anomaly scores for ML models
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize feature extractor with configurable parameters
        
        Args:
            config: Configuration dictionary with thresholds and window sizes
        """
        # Configuration with sensible defaults
        self.config = config or {}
        
        # Time windows (in seconds)
        self.windows = {
            'short': self.config.get('window_short', 60),      # 1 minute
            'medium': self.config.get('window_medium', 300),    # 5 minutes
            'long': self.config.get('window_long', 3600),       # 1 hour
            'very_long': self.config.get('window_very_long', 86400),  # 24 hours
        }
        
        # Thresholds for anomaly detection
        self.thresholds = {
            'brute_force_attempts': self.config.get('brute_force_threshold', 10),
            'dictionary_attack_attempts': self.config.get('dictionary_attack_threshold', 20),
            'ftp_anonymous_threshold': self.config.get('ftp_anonymous_threshold', 5),
            'session_rapid_switching': self.config.get('session_rapid_threshold', 10),
            'system_alert_rate': self.config.get('alert_rate_threshold', 5),
        }
        
        # User behavior tracking
        self.user_login_history = defaultdict(lambda: deque(maxlen=1000))
        self.user_auth_failures = defaultdict(lambda: defaultdict(lambda: deque(maxlen=1000)))
        self.user_session_history = defaultdict(list)
        self.user_active_sessions = {}
        
        # IP behavior tracking
        self.ip_activity = defaultdict(lambda: defaultdict(lambda: deque(maxlen=1000)))
        self.ip_failure_history = defaultdict(lambda: deque(maxlen=1000))
        self.ip_success_history = defaultdict(lambda: deque(maxlen=1000))
        self.ip_geo_lookup = {}  # Would integrate with GeoIP service
        
        # System health tracking
        self.system_events = deque(maxlen=1000)
        self.service_failures = defaultdict(lambda: deque(maxlen=1000))
        self.kernel_events = deque(maxlen=500)
        self.resource_warnings = deque(maxlen=500)
        
        # Attack pattern detection
        self.attack_patterns = defaultdict(lambda: deque(maxlen=100))
        self.distributed_attack_tracking = defaultdict(set)
        
        # Temporal patterns
        self.hourly_activity = defaultdict(list)
        self.weekly_patterns = defaultdict(list)
        
        # Session tracking
        self.session_metadata = {}
        
        # Statistical aggregates for anomaly detection
        self.stats = {
            'hourly_auth_rate': defaultdict(list),
            'hourly_ftp_rate': defaultdict(list),
            'hourly_system_events': defaultdict(list),
            'daily_user_activity': defaultdict(lambda: defaultdict(int)),
        }
        
        # Historical baseline (would be loaded from database in production)
        self.baseline = {
            'avg_auth_per_hour': 5,
            'std_auth_per_hour': 2,
            'avg_ftp_per_hour': 10,
            'std_ftp_per_hour': 5,
            'avg_session_duration': 3600,  # 1 hour
            'std_session_duration': 1800,
        }
        
    def extract(self, log) -> Dict:
        """
        Extract comprehensive features from a parsed log entry
        
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
        if event_type == "auth_failure" or event_type.startswith("auth_failure"):
            self._extract_auth_features(log, parsed, timestamp, features)
        elif event_type == "invalid_user":
            self._extract_invalid_user_features(log, parsed, timestamp, features)
        elif event_type == "session_open":
            self._extract_session_open_features(log, parsed, timestamp, features)
        elif event_type == "session_close":
            self._extract_session_close_features(log, parsed, timestamp, features)
        elif event_type.startswith("ftp"):
            self._extract_ftp_features(log, parsed, timestamp, features)
        elif event_type in ["logrotate_alert", "cups_shutdown", "cups_startup"]:
            self._extract_service_features(log, parsed, timestamp, features)
        elif event_type == "kernel_message":
            self._extract_kernel_features(log, parsed, timestamp, features)
        elif event_type in ["kerberos_auth", "kerberos_failed"]:
            self._extract_kerberos_features(log, parsed, timestamp, features)
        else:
            self._extract_other_features(log, parsed, timestamp, features)
        
        # Add time-window based aggregates
        self._add_temporal_features(timestamp, features)
        
        # Add attack pattern detection features
        self._detect_attack_patterns(log, parsed, timestamp, features)
        
        # Add anomaly scores
        self._calculate_anomaly_scores(features, event_type)
        
        # Calculate risk score
        features["risk_score"] = self._calculate_risk_score(features)
        features["risk_level"] = self._get_risk_level(features["risk_score"]).value
        
        # Add event type encoding for LSTM
        features["event_type_code"] = self._encode_event_type(event_type)
        
        return features
    
    def _extract_auth_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from authentication failure events"""
        user = parsed.get("user", "unknown")
        ip = parsed.get("ip", "unknown")
        
        # Track user and IP failures with timestamps
        self.user_auth_failures[user][ip].append(timestamp)
        self.ip_failure_history[ip].append(timestamp)
        
        # Clean old entries
        cutoff_short = timestamp - timedelta(seconds=self.windows['short'])
        cutoff_medium = timestamp - timedelta(seconds=self.windows['medium'])
        cutoff_long = timestamp - timedelta(seconds=self.windows['long'])
        
        # Count failures in different windows
        features["auth_failures_1min"] = sum(1 for t in self.ip_failure_history[ip] if t > cutoff_short)
        features["auth_failures_5min"] = sum(1 for t in self.ip_failure_history[ip] if t > cutoff_medium)
        features["auth_failures_1hour"] = sum(1 for t in self.ip_failure_history[ip] if t > cutoff_long)
        
        # User-specific failure counts
        user_failures_5min = 0
        for ip_addr, timestamps in self.user_auth_failures[user].items():
            user_failures_5min += sum(1 for t in timestamps if t > cutoff_medium)
        features["user_failures_5min"] = user_failures_5min
        
        # Unique IPs attempting login to this user
        features["unique_ips_user_5min"] = len([
            ip_addr for ip_addr, timestamps in self.user_auth_failures[user].items()
            if any(t > cutoff_medium for t in timestamps)
        ])
        
        # Failed attempts per IP in 5 minutes
        features["failures_per_ip_5min"] = features["auth_failures_5min"]
        
        # Track username patterns (potential dictionary attacks)
        usernames_attempted = set()
        for user_attempt, ip_dict in self.user_auth_failures.items():
            if any(any(t > cutoff_medium for t in timestamps) for timestamps in ip_dict.values()):
                usernames_attempted.add(user_attempt)
        features["distinct_usernames_5min"] = len(usernames_attempted)
        
        # Success ratio (tracking success after failures)
        recent_successes = sum(1 for t in self.ip_success_history[ip] if t > cutoff_medium)
        features["success_after_failure_5min"] = 1 if recent_successes > 0 else 0
        
        # Add IP reputation if available
        features["ip_reputation_score"] = self._get_ip_reputation(ip)
        
        # Add user-specific features
        features["is_privileged_user"] = 1 if user in ["root", "admin", "cyrus", "news"] else 0
        
        # Track this failure for hourly statistics
        self.stats['hourly_auth_rate'][timestamp.hour].append(timestamp)
        
    def _extract_invalid_user_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from invalid user attempts"""
        ip = parsed.get("ip", "unknown")
        
        # Track invalid user attempts
        self.ip_failure_history[ip].append(timestamp)
        
        cutoff_short = timestamp - timedelta(seconds=self.windows['short'])
        cutoff_medium = timestamp - timedelta(seconds=self.windows['medium'])
        
        features["invalid_users_1min"] = sum(1 for t in self.ip_failure_history[ip] if t > cutoff_short)
        features["invalid_users_5min"] = sum(1 for t in self.ip_failure_history[ip] if t > cutoff_medium)
        
        # Check for dictionary attack pattern (many usernames from same IP)
        usernames_attempted = set()
        for user_attempt, ip_dict in self.user_auth_failures.items():
            if ip in ip_dict and any(t > cutoff_medium for t in ip_dict[ip]):
                usernames_attempted.add(user_attempt)
        features["usernames_from_ip_5min"] = len(usernames_attempted)
        
    def _extract_session_open_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from session open events"""
        user = parsed.get("user", "unknown")
        uid = parsed.get("uid", "unknown")
        
        # Track session start
        self.user_active_sessions[user] = {
            'start_time': timestamp,
            'uid': uid
        }
        
        # Track session metadata
        self.session_metadata[user] = {
            'session_count': self.session_metadata.get(user, {}).get('session_count', 0) + 1,
            'last_session_start': timestamp
        }
        
        # Calculate time since last session
        if user in self.user_session_history:
            last_session = self.user_session_history[user][-1] if self.user_session_history[user] else None
            if last_session:
                features["time_since_last_session"] = (timestamp - last_session).total_seconds()
            else:
                features["time_since_last_session"] = -1
        else:
            features["time_since_last_session"] = -1
        
        # Track session count in time window
        self.user_session_history[user].append(timestamp)
        cutoff_medium = timestamp - timedelta(seconds=self.windows['medium'])
        features["session_count_5min"] = sum(1 for t in self.user_session_history[user] if t > cutoff_medium)
        
        # Check for rapid session switching
        cutoff_short = timestamp - timedelta(seconds=self.windows['short'])
        features["rapid_sessions_1min"] = sum(1 for t in self.user_session_history[user] if t > cutoff_short)
        
        # Add session features
        features["session_active"] = 1
        features["user_uid"] = uid
        
    def _extract_session_close_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from session close events"""
        user = parsed.get("user", "unknown")
        
        if user in self.user_active_sessions:
            session_start = self.user_active_sessions[user]['start_time']
            session_duration = (timestamp - session_start).total_seconds()
            
            features["session_duration"] = session_duration
            features["session_duration_hours"] = session_duration / 3600
            
            # Detect abnormally short or long sessions
            features["session_abnormally_short"] = 1 if session_duration < 60 else 0
            features["session_abnormally_long"] = 1 if session_duration > 28800 else 0  # > 8 hours
            
            # Track session duration for baseline
            self.user_session_history[f"{user}_duration"].append(session_duration)
            
            # Clean up
            del self.user_active_sessions[user]
        else:
            features["session_duration"] = 0
            features["session_abnormally_short"] = 0
            features["session_abnormally_long"] = 0
        
        features["session_active"] = 0
        
    def _extract_ftp_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from FTP events"""
        event_type = parsed.get("event_type")
        ip = parsed.get("ip", "unknown")
        
        # Track FTP connections
        self.ip_activity[ip]['ftp'].append(timestamp)
        
        cutoff_short = timestamp - timedelta(seconds=self.windows['short'])
        cutoff_medium = timestamp - timedelta(seconds=self.windows['medium'])
        cutoff_long = timestamp - timedelta(seconds=self.windows['long'])
        
        features["ftp_connections_1min"] = sum(1 for t in self.ip_activity[ip]['ftp'] if t > cutoff_short)
        features["ftp_connections_5min"] = sum(1 for t in self.ip_activity[ip]['ftp'] if t > cutoff_medium)
        features["ftp_connections_1hour"] = sum(1 for t in self.ip_activity[ip]['ftp'] if t > cutoff_long)
        
        # Check for anonymous FTP
        if event_type == "ftp_anonymous":
            features["is_anonymous_ftp"] = 1
            features["ftp_anonymous_count_5min"] = sum(
                1 for e in self.system_events 
                if e[0] == "ftp_anonymous" and e[1] > cutoff_medium
            )
            self.system_events.append(("ftp_anonymous", timestamp))
        else:
            features["is_anonymous_ftp"] = 0
            features["ftp_anonymous_count_5min"] = 0
        
        # Detect FTP scanning (many connections from same IP)
        features["ftp_scanning_detected"] = 1 if features["ftp_connections_1min"] > 10 else 0
        
        # Track for hourly statistics
        self.stats['hourly_ftp_rate'][timestamp.hour].append(timestamp)
        
    def _extract_service_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from system service events"""
        event_type = parsed.get("event_type")
        
        # Track service events
        self.system_events.append((event_type, timestamp))
        
        cutoff_medium = timestamp - timedelta(seconds=self.windows['medium'])
        cutoff_long = timestamp - timedelta(seconds=self.windows['long'])
        
        features["service_events_5min"] = sum(1 for e, t in self.system_events if t > cutoff_medium)
        features["service_events_1hour"] = sum(1 for e, t in self.system_events if t > cutoff_long)
        
        # Track specific service failures
        if "alert" in event_type or "shutdown" in event_type:
            service = parsed.get("process", "unknown")
            self.service_failures[service].append(timestamp)
            features[f"{service}_failures_1hour"] = sum(1 for t in self.service_failures[service] if t > cutoff_long)
        
        # Check for service failure rate anomaly
        features["service_failure_rate"] = features["service_events_5min"] / (self.windows['medium'] / 60) if features["service_events_5min"] > 0 else 0
        
    def _extract_kernel_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from kernel messages"""
        kernel_msg = parsed.get("kernel_message", "")
        
        # Track kernel events
        self.kernel_events.append((timestamp, kernel_msg))
        
        cutoff_medium = timestamp - timedelta(seconds=self.windows['medium'])
        
        # Check for specific kernel anomalies
        features["kernel_oops"] = 1 if "Oops" in kernel_msg else 0
        features["kernel_panic"] = 1 if "panic" in kernel_msg.lower() else 0
        features["kernel_hardware_error"] = 1 if any(word in kernel_msg.lower() for word in ["error", "failed", "fault"]) else 0
        
        # Count kernel warnings
        features["kernel_warnings_5min"] = sum(
            1 for t, msg in self.kernel_events 
            if t > cutoff_medium and ("warning" in msg.lower() or "error" in msg.lower())
        )
        
        # Memory/CPU related events
        features["memory_event"] = 1 if "memory" in kernel_msg.lower() else 0
        features["cpu_event"] = 1 if "cpu" in kernel_msg.lower() else 0
        features["disk_event"] = 1 if any(word in kernel_msg.lower() for word in ["disk", "scsi", "ata"]) else 0
        
        # Track resource warnings
        if features["kernel_warnings_5min"] > 0:
            self.resource_warnings.append(timestamp)
        
    def _extract_kerberos_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from Kerberos authentication events"""
        ip = parsed.get("ip", "unknown")
        
        # Track Kerberos failures
        self.ip_activity[ip]['kerberos'].append(timestamp)
        
        cutoff_medium = timestamp - timedelta(seconds=self.windows['medium'])
        
        features["kerberos_failures_5min"] = sum(1 for t in self.ip_activity[ip]['kerberos'] if t > cutoff_medium)
        features["kerberos_failure_rate"] = features["kerberos_failures_5min"] / (self.windows['medium'] / 60)
        
    def _extract_other_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from other event types"""
        # Track general activity
        self.system_events.append(("other", timestamp))
        
        cutoff_medium = timestamp - timedelta(seconds=self.windows['medium'])
        features["other_events_5min"] = sum(1 for e, t in self.system_events if t > cutoff_medium and e == "other")
        
    def _add_temporal_features(self, timestamp: datetime, features: Dict):
        """Add time-based aggregate features"""
        # Track hourly activity
        self.hourly_activity[timestamp.hour].append(timestamp)
        
        # Clean old entries (keep last 7 days)
        cutoff = timestamp - timedelta(days=7)
        for hour in list(self.hourly_activity.keys()):
            self.hourly_activity[hour] = [t for t in self.hourly_activity[hour] if t > cutoff]
        
        # Calculate activity ratios
        current_hour = timestamp.hour
        if self.hourly_activity[current_hour]:
            features["hour_activity"] = len(self.hourly_activity[current_hour])
            
            # Compare to average of other hours
            other_hours_activity = []
            for hour, events in self.hourly_activity.items():
                if hour != current_hour and events:
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
        self.weekly_patterns[dow].append(timestamp)
        cutoff_weekly = timestamp - timedelta(days=30)
        self.weekly_patterns[dow] = [t for t in self.weekly_patterns[dow] if t > cutoff_weekly]
        
        features["dow_activity"] = len(self.weekly_patterns[dow])
        
    def _detect_attack_patterns(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Detect various attack patterns"""
        event_type = parsed.get("event_type")
        
        # Brute force detection
        if features.get("auth_failures_5min", 0) > self.thresholds['brute_force_attempts']:
            features["brute_force_detected"] = 1
            features["anomaly_type"] = AnomalyType.BRUTE_FORCE.value
            self.attack_patterns['brute_force'].append(timestamp)
        else:
            features["brute_force_detected"] = 0
        
        # Dictionary attack detection (many usernames from same IP)
        if features.get("usernames_from_ip_5min", 0) > self.thresholds['dictionary_attack_attempts']:
            features["dictionary_attack_detected"] = 1
            features["anomaly_type"] = AnomalyType.DICTIONARY_ATTACK.value
            self.attack_patterns['dictionary'].append(timestamp)
        else:
            features["dictionary_attack_detected"] = 0
        
        # Distributed attack detection (many IPs targeting same user)
        if features.get("unique_ips_user_5min", 0) > 5:
            features["distributed_attack_detected"] = 1
            features["anomaly_type"] = AnomalyType.DISTRIBUTED_ATTACK.value
            
            # Track IPs involved
            user = parsed.get("user", "unknown")
            ip = parsed.get("ip", "unknown")
            self.distributed_attack_tracking[user].add(ip)
            features["distributed_attack_ips"] = len(self.distributed_attack_tracking[user])
        else:
            features["distributed_attack_detected"] = 0
            features["distributed_attack_ips"] = 0
        
        # Anonymous FTP abuse
        if features.get("ftp_anonymous_count_5min", 0) > self.thresholds['ftp_anonymous_threshold']:
            features["ftp_abuse_detected"] = 1
            features["anomaly_type"] = AnomalyType.ANONYMOUS_FTP.value
        else:
            features["ftp_abuse_detected"] = 0
        
        # Rapid session switching (potential account sharing or automation)
        if features.get("rapid_sessions_1min", 0) > self.thresholds['session_rapid_switching']:
            features["rapid_session_detected"] = 1
            features["anomaly_type"] = AnomalyType.RAPID_SESSION.value
        else:
            features["rapid_session_detected"] = 0
        
        # Suspicious hour activity
        if features.get("is_night_hours", 0) and features.get("hour_activity_ratio", 1) > 3:
            features["suspicious_hour_detected"] = 1
            features["anomaly_type"] = AnomalyType.SUSPICIOUS_HOUR.value
        else:
            features["suspicious_hour_detected"] = 0
        
        # Rate anomaly detection
        if features.get("auth_failures_5min", 0) > self.baseline['avg_auth_per_hour'] + (2 * self.baseline['std_auth_per_hour']):
            features["rate_anomaly_detected"] = 1
            features["anomaly_type"] = AnomalyType.RATE_ANOMALY.value
        else:
            features["rate_anomaly_detected"] = 0
        
        # Service failure anomaly
        if features.get("service_failure_rate", 0) > self.thresholds['system_alert_rate']:
            features["service_failure_detected"] = 1
            features["anomaly_type"] = AnomalyType.SERVICE_FAILURE.value
        else:
            features["service_failure_detected"] = 0
        
        # Set anomaly flag if any detected
        features["anomaly_detected"] = 1 if any([
            features["brute_force_detected"],
            features["dictionary_attack_detected"],
            features["distributed_attack_detected"],
            features["ftp_abuse_detected"],
            features["rapid_session_detected"],
            features["suspicious_hour_detected"],
            features["rate_anomaly_detected"],
            features["service_failure_detected"]
        ]) else 0
        
    def _calculate_anomaly_scores(self, features: Dict, event_type: str):
        """Calculate anomaly scores for ML model"""
        anomaly_score = 0.0
        
        # Authentication anomaly score
        if features.get("auth_failures_5min", 0) > self.baseline['avg_auth_per_hour']:
            deviation = (features["auth_failures_5min"] - self.baseline['avg_auth_per_hour']) / (self.baseline['std_auth_per_hour'] + 1)
            anomaly_score += min(deviation * 0.2, 0.5)
        
        # Session anomaly score
        if features.get("session_duration", 0) > 0:
            deviation = abs(features["session_duration"] - self.baseline['avg_session_duration']) / (self.baseline['std_session_duration'] + 1)
            anomaly_score += min(deviation * 0.1, 0.3)
        
        # FTP anomaly score
        if features.get("ftp_connections_5min", 0) > self.baseline['avg_ftp_per_hour']:
            deviation = (features["ftp_connections_5min"] - self.baseline['avg_ftp_per_hour']) / (self.baseline['std_ftp_per_hour'] + 1)
            anomaly_score += min(deviation * 0.15, 0.4)
        
        # System anomaly score
        if features.get("service_events_5min", 0) > 3:
            anomaly_score += min(features["service_events_5min"] * 0.05, 0.3)
        
        # Attack pattern score
        if features.get("brute_force_detected", 0):
            anomaly_score += 0.5
        if features.get("dictionary_attack_detected", 0):
            anomaly_score += 0.4
        if features.get("distributed_attack_detected", 0):
            anomaly_score += 0.6
        
        features["anomaly_score"] = min(anomaly_score, 1.0)
        
    def _calculate_risk_score(self, features: Dict) -> int:
        """
        Calculate comprehensive risk score (0-100)
        
        Higher score indicates higher risk/priority
        """
        risk_score = 0
        
        # Authentication failures (up to 40 points)
        risk_score += min(features.get("auth_failures_5min", 0) * 2, 25)
        risk_score += min(features.get("invalid_users_5min", 0) * 3, 15)
        
        # Attack patterns (up to 30 points)
        if features.get("brute_force_detected", 0):
            risk_score += 15
        if features.get("dictionary_attack_detected", 0):
            risk_score += 10
        if features.get("distributed_attack_detected", 0):
            risk_score += 20
        if features.get("ftp_abuse_detected", 0):
            risk_score += 10
        
        # System health (up to 20 points)
        risk_score += min(features.get("service_events_5min", 0) * 2, 10)
        risk_score += min(features.get("kernel_warnings_5min", 0) * 3, 10)
        
        # Suspicious patterns (up to 10 points)
        if features.get("suspicious_hour_detected", 0):
            risk_score += 5
        if features.get("rapid_session_detected", 0):
            risk_score += 5
        
        # Add IP reputation penalty
        ip_reputation = features.get("ip_reputation_score", 0)
        if ip_reputation > 0:
            risk_score += ip_reputation * 10
        
        return min(risk_score, 100)
    
    def _get_risk_level(self, risk_score: int) -> RiskLevel:
        """Get risk level based on risk score"""
        if risk_score >= 80:
            return RiskLevel.CRITICAL
        elif risk_score >= 60:
            return RiskLevel.HIGH
        elif risk_score >= 30:
            return RiskLevel.MEDIUM
        elif risk_score >= 10:
            return RiskLevel.LOW
        elif risk_score > 0:
            return RiskLevel.INFO
        else:
            return RiskLevel.NONE
    
    def _encode_event_type(self, event_type: str) -> int:
        """Encode event type for LSTM model"""
        event_encoding = {
            "auth_failure": 1,
            "auth_failure_root": 2,
            "auth_failure_guest": 3,
            "auth_failure_test": 4,
            "invalid_user": 5,
            "session_open": 6,
            "session_close": 7,
            "ftp_connection": 8,
            "ftp_anonymous": 9,
            "ftp_timeout": 10,
            "logrotate_alert": 11,
            "cups_shutdown": 12,
            "cups_startup": 13,
            "syslog_restart": 14,
            "snmp_packet": 15,
            "kernel_message": 16,
            "memory_info": 17,
            "cpu_info": 18,
            "bios_e820": 19,
            "kerberos_auth": 20,
            "kerberos_failed": 21,
            "gdm_auth_failure": 22,
            "gdm_auth_failed": 23,
            "named_notify": 24,
            "xinetd_warning": 25,
            "ftp_getpeername": 26,
            "udev_remove": 27,
            "udev_create": 28,
            "gpm_info": 29,
            "gpm_auto": 30,
            "root_login": 31,
            "service_startup": 32,
            "network_setting": 33,
            "network_loopback": 34,
            "system_alert": 35,
            "other": 0
        }
        return event_encoding.get(event_type, 0)
    
    def _get_ip_reputation(self, ip: str) -> float:
        """
        Get IP reputation score (0-1, higher = worse)
        
        In production, this would integrate with:
        - Threat intelligence feeds
        - GeoIP databases
        - Historical abuse databases
        """
        # Simplified implementation for now
        # Would be replaced with actual IP reputation service
        suspicious_networks = [
            "218.188.2.4", "220-135-151-1", "218.22.3.51", "61.53.154.93",
            "211.46.224.253", "217.60.212.66", "209.152.168.249"
        ]
        
        if any(net in ip for net in suspicious_networks):
            return 0.8
        return 0.0
    
    def get_health_report(self) -> Dict:
        """
        Generate comprehensive system health report
        
        Returns:
            Dictionary with health metrics and recommendations
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "security": {},
            "system_health": {},
            "recommendations": []
        }
        
        # Security summary
        total_attacks = len(self.attack_patterns['brute_force']) + len(self.attack_patterns['dictionary'])
        report["security"]["total_attacks_detected"] = total_attacks
        report["security"]["unique_attacking_ips"] = len(set(
            ip for pattern in self.attack_patterns.values() 
            for _, ip in pattern
        ))
        
        # Top attacked users
        attacked_users = sorted(
            [(user, len(failures)) for user, failures in self.user_auth_failures.items()],
            key=lambda x: x[1], reverse=True
        )[:10]
        report["security"]["top_attacked_users"] = attacked_users
        
        # System health
        report["system_health"]["service_failures"] = {
            service: len(failures) 
            for service, failures in self.service_failures.items()
        }
        report["system_health"]["kernel_events_count"] = len(self.kernel_events)
        report["system_health"]["resource_warnings"] = len(self.resource_warnings)
        
        # Recommendations
        if total_attacks > 50:
            report["recommendations"].append("High number of attacks detected. Consider implementing IP blocking or rate limiting.")
        if len(self.resource_warnings) > 10:
            report["recommendations"].append("System resource warnings detected. Investigate hardware or configuration issues.")
        if len(self.service_failures) > 5:
            report["recommendations"].append("Multiple service failures detected. Check system stability.")
        
        return report
