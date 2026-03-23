from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Optional
import numpy as np


class WindowsFeatureExtractor:
    """
    Stateful feature extractor for Windows CBS/CSI logs.
    Designed for LSTM + anomaly detection + system health analytics.
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
            'medium': self.config.get('window_medium', 300),   # 5 minutes
            'long': self.config.get('window_long', 3600),      # 1 hour
            'very_long': self.config.get('window_very_long', 86400),  # 24 hours
        }
        
        # Thresholds for anomaly detection
        self.thresholds = {
            'package_failure_threshold': self.config.get('package_failure_threshold', 5),
            'error_rate_threshold': self.config.get('error_rate_threshold', 10),
            'hresult_error_threshold': self.config.get('hresult_error_threshold', 3),
            'reboot_frequency': self.config.get('reboot_frequency_threshold', 5),
        }
        
        # ===== Package Tracking =====
        self.package_operations = defaultdict(lambda: deque(maxlen=1000))
        self.package_failures = defaultdict(lambda: deque(maxlen=1000))
        self.package_successes = defaultdict(lambda: deque(maxlen=1000))
        
        # ===== HRESULT Tracking =====
        self.hresult_errors = defaultdict(lambda: deque(maxlen=1000))
        self.hresult_types = defaultdict(lambda: defaultdict(lambda: deque(maxlen=1000)))
        
        # ===== Session Tracking =====
        self.sessions = defaultdict(lambda: deque(maxlen=1000))
        self.active_sessions = {}
        
        # ===== Transaction Tracking =====
        self.transactions = defaultdict(lambda: deque(maxlen=1000))
        self.transaction_sequences = defaultdict(lambda: deque(maxlen=500))
        
        # ===== System Health Tracking =====
        self.system_errors = deque(maxlen=1000)
        self.reboot_events = deque(maxlen=100)
        self.service_failures = defaultdict(lambda: deque(maxlen=1000))
        
        # ===== Temporal Patterns =====
        self.hourly_events = defaultdict(list)
        self.daily_patterns = defaultdict(list)
        
        # ===== Statistical Baseline =====
        self.baseline = {
            'avg_package_ops_per_hour': 50,
            'std_package_ops_per_hour': 20,
            'avg_errors_per_hour': 5,
            'std_errors_per_hour': 3,
            'avg_transactions_per_hour': 100,
            'std_transactions_per_hour': 30,
        }
        
    def extract(self, log) -> Dict:
        """
        Extract comprehensive features from a parsed Windows log entry
        
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
        if event_type.startswith("csi_"):
            self._extract_csi_features(log, parsed, timestamp, features)
        elif event_type.startswith("cbs_"):
            self._extract_cbs_features(log, parsed, timestamp, features)
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
        features["level_code"] = self._encode_level(parsed.get("level", "Info"))
        
        return features
    
    def _extract_csi_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from CSI (Component Servicing Infrastructure) events"""
        event_type = parsed.get("event_type")
        
        # Track transactions
        if "transaction" in event_type:
            if "created" in event_type or "create" in event_type:
                seq_num = parsed.get("transaction_seq", "0")
                self.transactions[seq_num].append(timestamp)
                features["transaction_active"] = 1
                
                # Track transaction sequence
                self.transaction_sequences[seq_num].append({
                    'timestamp': timestamp,
                    'event_type': event_type,
                    'seq': parsed.get("sequence", "0")
                })
            elif "destroyed" in event_type:
                features["transaction_active"] = 0
                features["transaction_completed"] = 1
            else:
                features["transaction_active"] = 0
                features["transaction_completed"] = 0
        else:
            features["transaction_active"] = 0
            features["transaction_completed"] = 0
        
        # Track operations
        if parsed.get("operations_count"):
            try:
                features["operations_count"] = int(parsed.get("operations_count", 0))
            except ValueError:
                features["operations_count"] = 0
        else:
            features["operations_count"] = 0
        
        # Track non-lock operations
        if parsed.get("non_lock_operations"):
            try:
                features["non_lock_ops"] = int(parsed.get("non_lock_operations", 0))
            except ValueError:
                features["non_lock_ops"] = 0
        else:
            features["non_lock_ops"] = 0
        
        # Track sequence numbers for transaction continuity
        if parsed.get("sequence"):
            try:
                seq = int(parsed.get("sequence", 0))
                self.transaction_sequences['global'].append((timestamp, seq))
                
                # Calculate time between sequences
                if len(self.transaction_sequences['global']) > 1:
                    last_seq, last_time = self.transaction_sequences['global'][-2]
                    features["time_since_last_sequence"] = (timestamp - last_time).total_seconds()
                    features["sequence_gap"] = seq - last_seq if last_seq > 0 else 0
                else:
                    features["time_since_last_sequence"] = 0
                    features["sequence_gap"] = 0
            except (ValueError, TypeError):
                features["time_since_last_sequence"] = 0
                features["sequence_gap"] = 0
        else:
            features["time_since_last_sequence"] = 0
            features["sequence_gap"] = 0
        
        # Track WCP initialization
        if event_type == "csi_wcp_init":
            wcp_version = parsed.get("wcp_version", "0.0.0.0")
            try:
                version_parts = wcp_version.split('.')
                features["wcp_version_major"] = int(version_parts[0]) if len(version_parts) > 0 else 0
                features["wcp_version_minor"] = int(version_parts[1]) if len(version_parts) > 1 else 0
                features["wcp_version_patch"] = int(version_parts[2]) if len(version_parts) > 2 else 0
            except (ValueError, IndexError):
                features["wcp_version_major"] = 0
                features["wcp_version_minor"] = 0
                features["wcp_version_patch"] = 0
        else:
            features["wcp_version_major"] = 0
            features["wcp_version_minor"] = 0
            features["wcp_version_patch"] = 0
        
        # Track store size changes
        if parsed.get("store_size"):
            try:
                features["store_size"] = int(parsed.get("store_size", 0))
            except ValueError:
                features["store_size"] = 0
        else:
            features["store_size"] = 0
    
    def _extract_cbs_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from CBS (Component-Based Servicing) events"""
        event_type = parsed.get("event_type")
        
        # Track package operations
        if "package" in event_type or parsed.get("package_name"):
            package_name = parsed.get("package_name", "unknown")
            self.package_operations[package_name].append(timestamp)
            
            cutoff_medium = timestamp - timedelta(seconds=self.windows['medium'])
            features["package_ops_5min"] = sum(1 for t in self.package_operations[package_name] if t > cutoff_medium)
            
            # Track package failures vs successes
            if "failed" in event_type:
                self.package_failures[package_name].append(timestamp)
                features["package_failure"] = 1
                features["package_success"] = 0
            elif "read" in event_type or "loaded" in event_type:
                self.package_successes[package_name].append(timestamp)
                features["package_failure"] = 0
                features["package_success"] = 1
            else:
                features["package_failure"] = 0
                features["package_success"] = 0
            
            # Track applicable and current states
            if parsed.get("applicable_state"):
                try:
                    features["applicable_state"] = int(parsed.get("applicable_state", 0))
                except ValueError:
                    features["applicable_state"] = 0
            else:
                features["applicable_state"] = 0
            
            if parsed.get("current_state"):
                try:
                    features["current_state"] = int(parsed.get("current_state", 0))
                except ValueError:
                    features["current_state"] = 0
            else:
                features["current_state"] = 0
            
            # State mismatch detection (indicates potential issues)
            features["state_mismatch"] = 1 if features["applicable_state"] != features["current_state"] else 0
        else:
            features["package_ops_5min"] = 0
            features["package_failure"] = 0
            features["package_success"] = 0
            features["applicable_state"] = 0
            features["current_state"] = 0
            features["state_mismatch"] = 0
        
        # Track HRESULT errors
        if parsed.get("hresult"):
            hresult = parsed.get("hresult")
            self.hresult_errors[hresult].append(timestamp)
            features["has_hresult"] = 1
            features["hresult_error_count_5min"] = len([
                t for t in self.hresult_errors[hresult] 
                if t > timestamp - timedelta(seconds=self.windows['medium'])
            ])
            
            # Classify HRESULT type
            if "80004005" in hresult:  # E_FAIL
                features["hresult_type"] = 1
                features["is_e_fail"] = 1
            elif "800f080d" in hresult:  # CBS_E_MANIFEST_INVALID_ITEM
                features["hresult_type"] = 2
                features["is_manifest_invalid"] = 1
            elif "800f0805" in hresult:  # CBS_E_INVALID_PACKAGE
                features["hresult_type"] = 3
                features["is_invalid_package"] = 1
            elif "80070001" in hresult:  # ERROR_INVALID_FUNCTION
                features["hresult_type"] = 4
                features["is_invalid_function"] = 1
            else:
                features["hresult_type"] = 0
                features["is_e_fail"] = 0
                features["is_manifest_invalid"] = 0
                features["is_invalid_package"] = 0
                features["is_invalid_function"] = 0
        else:
            features["has_hresult"] = 0
            features["hresult_error_count_5min"] = 0
            features["hresult_type"] = 0
            features["is_e_fail"] = 0
            features["is_manifest_invalid"] = 0
            features["is_invalid_package"] = 0
            features["is_invalid_function"] = 0
        
        # Track sessions
        if "session" in event_type:
            session_id = parsed.get("session_id", "unknown")
            self.sessions[session_id].append(timestamp)
            features["session_active"] = 1
            features["session_count_1hour"] = len([
                t for t in self.sessions[session_id] 
                if t > timestamp - timedelta(seconds=self.windows['long'])
            ])
        else:
            features["session_active"] = 0
            features["session_count_1hour"] = 0
        
        # Track scavenge operations
        if "scavenge" in event_type:
            features["scavenge_event"] = 1
            features["scavenge_completed"] = 1 if "completed" in event_type else 0
        else:
            features["scavenge_event"] = 0
            features["scavenge_completed"] = 0
        
        # Track reboot marks
        if "reboot" in event_type:
            self.reboot_events.append(timestamp)
            features["reboot_event"] = 1
            features["reboot_count_1hour"] = len([
                t for t in self.reboot_events 
                if t > timestamp - timedelta(seconds=self.windows['long'])
            ])
        else:
            features["reboot_event"] = 0
            features["reboot_count_1hour"] = 0
        
        # Track SQM events (software quality metrics)
        if "sqm" in event_type:
            features["sqm_event"] = 1
            features["sqm_failure"] = 1 if "failed" in event_type else 0
        else:
            features["sqm_event"] = 0
            features["sqm_failure"] = 0
        
        # Track offline registry operations
        if "offline" in event_type or "hive" in event_type:
            features["offline_operation"] = 1
        else:
            features["offline_operation"] = 0
        
        # Track error rate
        cutoff_medium = timestamp - timedelta(seconds=self.windows['medium'])
        error_events = [e for e in self.system_errors if e > cutoff_medium]
        features["error_count_5min"] = len(error_events)
        
        # Track warnings
        if "warning" in event_type:
            self.system_errors.append(timestamp)
            features["warning_event"] = 1
        else:
            features["warning_event"] = 0
        
        # Track service failures
        if "failed" in event_type:
            self.service_failures['cbs'].append(timestamp)
            features["cbs_failure_count_5min"] = len([
                t for t in self.service_failures['cbs'] 
                if t > cutoff_medium
            ])
        else:
            features["cbs_failure_count_5min"] = 0
        
        # Track trusted installer lifecycle
        if "trustedinstaller" in event_type.lower():
            if "start" in event_type:
                features["trusted_installer_start"] = 1
                features["trusted_installer_end"] = 0
            elif "end" in event_type:
                features["trusted_installer_start"] = 0
                features["trusted_installer_end"] = 1
            else:
                features["trusted_installer_start"] = 0
                features["trusted_installer_end"] = 0
        else:
            features["trusted_installer_start"] = 0
            features["trusted_installer_end"] = 0
    
    def _extract_other_features(self, log, parsed: Dict, timestamp: datetime, features: Dict):
        """Extract features from other event types"""
        # Generic tracking
        cutoff_medium = timestamp - timedelta(seconds=self.windows['medium'])
        
        # Track unknown events
        self.system_errors.append(timestamp)
        
        features["error_count_5min"] = len([
            t for t in self.system_errors if t > cutoff_medium
        ])
        features["package_ops_5min"] = 0
        features["package_failure"] = 0
        features["package_success"] = 0
        features["has_hresult"] = 0
        features["session_active"] = 0
        features["scavenge_event"] = 0
        features["reboot_event"] = 0
        features["sqm_event"] = 0
        features["warning_event"] = 0
        features["trusted_installer_start"] = 0
        features["trusted_installer_end"] = 0
    
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
        
        # Package operation anomaly
        if features.get("package_ops_5min", 0) > self.baseline['avg_package_ops_per_hour'] / 12:
            deviation = (features["package_ops_5min"] - self.baseline['avg_package_ops_per_hour'] / 12) / (self.baseline['std_package_ops_per_hour'] / 12 + 1)
            anomaly_score += min(deviation * 0.2, 0.4)
        
        # Error rate anomaly
        if features.get("error_count_5min", 0) > self.baseline['avg_errors_per_hour'] / 12:
            deviation = (features["error_count_5min"] - self.baseline['avg_errors_per_hour'] / 12) / (self.baseline['std_errors_per_hour'] / 12 + 1)
            anomaly_score += min(deviation * 0.3, 0.5)
        
        # Package failure anomaly
        if features.get("package_failure", 0):
            failure_count = features.get("package_ops_5min", 0)
            if failure_count > self.thresholds['package_failure_threshold']:
                anomaly_score += min(failure_count * 0.05, 0.4)
        
        # HRESULT error anomaly
        if features.get("has_hresult", 0) and features.get("hresult_error_count_5min", 0) > self.thresholds['hresult_error_threshold']:
            anomaly_score += 0.3
        
        # State mismatch anomaly (package state inconsistency)
        if features.get("state_mismatch", 0):
            anomaly_score += 0.2
        
        # Reboot frequency anomaly
        if features.get("reboot_count_1hour", 0) > self.thresholds['reboot_frequency']:
            anomaly_score += min(features["reboot_count_1hour"] * 0.1, 0.5)
        
        # SQM failure anomaly
        if features.get("sqm_failure", 0):
            anomaly_score += 0.2
        
        # Hour activity ratio anomaly
        if features.get("hour_activity_ratio", 1) > 2:
            anomaly_score += min((features["hour_activity_ratio"] - 1) * 0.1, 0.3)
        
        features["anomaly_score"] = min(anomaly_score, 1.0)
    
    def _calculate_risk_score(self, features: Dict) -> int:
        """
        Calculate comprehensive risk score (0-100)
        
        Higher score indicates higher risk/priority
        """
        risk_score = 0
        
        # Package failures (up to 30 points)
        if features.get("package_failure", 0):
            risk_score += min(features.get("package_ops_5min", 0) * 2, 20)
            risk_score += 10 if features.get("state_mismatch", 0) else 0
        
        # HRESULT errors (up to 30 points)
        if features.get("has_hresult", 0):
            risk_score += min(features.get("hresult_error_count_5min", 0) * 5, 25)
            
            # Higher penalty for specific error types
            if features.get("is_e_fail", 0):
                risk_score += 10
            elif features.get("is_manifest_invalid", 0):
                risk_score += 15
            elif features.get("is_invalid_package", 0):
                risk_score += 20
        
        # System health (up to 20 points)
        risk_score += min(features.get("error_count_5min", 0) * 2, 15)
        risk_score += min(features.get("reboot_count_1hour", 0) * 5, 15)
        
        # SQM failures (up to 10 points)
        if features.get("sqm_failure", 0):
            risk_score += 10
        
        # Anomaly score contribution (up to 10 points)
        risk_score += features.get("anomaly_score", 0) * 10
        
        return min(risk_score, 100)
    
    def _encode_event_type(self, event_type: str) -> int:
        """Encode event type for LSTM model"""
        event_encoding = {
            # CSI events (1-20)
            "csi_transaction_created": 1,
            "csi_transaction_create": 2,
            "csi_perf_trace": 3,
            "csi_store_initialized": 4,
            "csi_resolve_pending": 5,
            "csi_commit": 6,
            "csi_perform_ops": 7,
            "csi_store_coherency": 8,
            "csi_transaction_destroyed": 9,
            "csi_transaction_initialized": 10,
            "csi_populate_begin": 11,
            "csi_populate_end": 12,
            "csi_wcp_init": 13,
            
            # CBS events (21-50)
            "cbs_manifest_caching_disabled": 21,
            "cbs_end_main_loop": 22,
            "cbs_end_finalization": 23,
            "cbs_end_initialization": 24,
            "cbs_expecting_attribute": 25,
            "cbs_backup_log_failed": 26,
            "cbs_failed_get_element": 27,
            "cbs_failed_open_package": 28,
            "cbs_idle_thread_terminated": 29,
            "cbs_loaded_servicing_stack": 30,
            "cbs_load_offline_hive": 31,
            "cbs_no_startup_required": 32,
            "cbs_nonstart_check": 33,
            "cbs_nonstart_success": 34,
            "cbs_offline_readonly": 35,
            "cbs_read_cached_package": 36,
            "cbs_reboot_incremented": 37,
            "cbs_reboot_refs": 38,
            "cbs_scavenge_begin": 39,
            "cbs_scavenge_completed": 40,
            "cbs_scavenge_starts": 41,
            "cbs_session_spp": 42,
            "cbs_session_init": 43,
            "cbs_sqm_cleanup": 44,
            "cbs_sqm_failed_std_upload": 45,
            "cbs_sqm_failed_upload": 46,
            "cbs_sqm_initializing": 47,
            "cbs_sqm_queued": 48,
            "cbs_sqm_request_upload": 49,
            "cbs_sqm_upload_warning": 50,
            "cbs_start_main_loop": 51,
            "cbs_start_finalization": 52,
            "cbs_start_initialization": 53,
            "cbs_startup_thread_terminated": 54,
            "cbs_service_started": 55,
            "cbs_unload_offline_hive": 56,
            "cbs_warning_unrecognized": 57,
            
            "other": 0
        }
        return event_encoding.get(event_type, 0)
    
    def _encode_level(self, level: str) -> int:
        """Encode log level for LSTM model"""
        level_encoding = {
            "Info": 1,
            "Warning": 2,
            "Error": 3,
            "Fatal": 4
        }
        return level_encoding.get(level, 0)
    
    def get_health_report(self) -> Dict:
        """
        Generate comprehensive Windows system health report
        
        Returns:
            Dictionary with health metrics and recommendations
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "package_health": {},
            "system_health": {},
            "error_analysis": {},
            "recommendations": []
        }
        
        # Package health summary
        total_package_ops = sum(len(ops) for ops in self.package_operations.values())
        total_package_failures = sum(len(fails) for fails in self.package_failures.values())
        
        report["package_health"]["total_operations"] = total_package_ops
        report["package_health"]["total_failures"] = total_package_failures
        report["package_health"]["failure_rate"] = (
            total_package_failures / total_package_ops if total_package_ops > 0 else 0
        )
        
        # Most problematic packages
        problematic_packages = sorted(
            [(pkg, len(fails)) for pkg, fails in self.package_failures.items()],
            key=lambda x: x[1], reverse=True
        )[:10]
        report["package_health"]["problematic_packages"] = problematic_packages
        
        # System health
        report["system_health"]["reboot_count"] = len(self.reboot_events)
        report["system_health"]["error_count"] = len(self.system_errors)
        report["system_health"]["service_failures"] = {
            service: len(failures) 
            for service, failures in self.service_failures.items()
        }
        
        # Error analysis
        hresult_summary = {
            hresult: len(events) 
            for hresult, events in self.hresult_errors.items()
        }
        report["error_analysis"]["hresult_distribution"] = hresult_summary
        
        # Recommendations
        if total_package_failures > 50:
            report["recommendations"].append("High number of package failures detected. Check Windows Update and CBS component health.")
        
        if len(self.reboot_events) > 3:
            report["recommendations"].append("Multiple reboot events detected. Investigate if reboots are planned or caused by updates.")
        
        if "800f0805" in hresult_summary:
            report["recommendations"].append("Invalid package errors detected. Run DISM /Online /Cleanup-Image /RestoreHealth")
        
        if "800f080d" in hresult_summary:
            report["recommendations"].append("Manifest invalid errors detected. Check for corrupted CBS manifests.")
        
        if len(self.system_errors) > 100:
            report["recommendations"].append("High error rate detected. Investigate system stability.")
        
        return report
