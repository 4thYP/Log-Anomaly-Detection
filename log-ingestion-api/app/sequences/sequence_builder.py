from collections import defaultdict, deque
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
import numpy as np
from datetime import datetime, timedelta


class SequenceType(Enum):
    """Types of sequences that can be generated"""
    EVENT_TYPE = "event_type_sequence"
    RISK_SCORE = "risk_score_sequence"
    ATTACK_PATTERN = "attack_pattern_sequence"
    SESSION_BEHAVIOR = "session_behavior_sequence"
    AUTH_BEHAVIOR = "auth_behavior_sequence"
    SYSTEM_HEALTH = "system_health_sequence"
    NETWORK_ACTIVITY = "network_activity_sequence"
    COMBINED = "combined_sequence"


class SequenceBuilder:
    """
    Advanced sequence builder for LSTM training and inference.
    
    Features:
    - Maintains separate sequences per server (sid)
    - Supports multiple sequence types for different models
    - Schema-aware feature extraction
    - Sliding windows with configurable parameters
    - Handles variable-length sequences
    - Supports feature normalization
    - Maintains sequence metadata for training
    """
    
    def __init__(self, 
                 sequence_length: int = 10,
                 stride: int = 1,
                 min_sequence_length: int = 3,
                 max_sequences_per_server: int = 1000,
                 enable_all_sequence_types: bool = True,
                 feature_config: Optional[Dict] = None):
        """
        Initialize sequence builder with configuration
        
        Args:
            sequence_length: Length of each sequence
            stride: Stride for sliding window (1 = every event, 2 = every other event)
            min_sequence_length: Minimum length before returning sequence
            max_sequences_per_server: Max number of sequences to store per server
            enable_all_sequence_types: Whether to generate all sequence types
            feature_config: Configuration for feature normalization
        """
        self.sequence_length = sequence_length
        self.stride = stride
        self.min_sequence_length = min_sequence_length
        self.max_sequences_per_server = max_sequences_per_server
        
        # Store raw feature sequences per server and type
        self.server_sequences = defaultdict(lambda: {
            SequenceType.EVENT_TYPE: deque(maxlen=sequence_length * 2),
            SequenceType.RISK_SCORE: deque(maxlen=sequence_length * 2),
            SequenceType.ATTACK_PATTERN: deque(maxlen=sequence_length * 2),
            SequenceType.SESSION_BEHAVIOR: deque(maxlen=sequence_length * 2),
            SequenceType.AUTH_BEHAVIOR: deque(maxlen=sequence_length * 2),
            SequenceType.SYSTEM_HEALTH: deque(maxlen=sequence_length * 2),
            SequenceType.NETWORK_ACTIVITY: deque(maxlen=sequence_length * 2),
            SequenceType.COMBINED: deque(maxlen=sequence_length * 2)
        })
        
        # Store feature vectors for combined sequence
        self.combined_vectors = defaultdict(lambda: deque(maxlen=sequence_length * 2))
        
        # Track session state per server
        self.session_state = defaultdict(lambda: {
            'current_sessions': {},  # user -> start_time
            'session_count': 0,
            'session_history': deque(maxlen=100)
        })
        
        # Track attack pattern state
        self.attack_state = defaultdict(lambda: {
            'active_attacks': set(),
            'attack_history': deque(maxlen=100)
        })
        
        # Track auth behavior state
        self.auth_state = defaultdict(lambda: {
            'recent_failures': deque(maxlen=50),
            'recent_successes': deque(maxlen=50),
            'user_failure_count': defaultdict(int)
        })
        
        # Feature normalization parameters
        self.feature_config = feature_config or {
            'normalize': True,
            'feature_ranges': {
                'event_type_code': (0, 35),
                'risk_score': (0, 100),
                'session_duration': (0, 86400),
                'auth_failure_count': (0, 100),
                'attack_severity': (0, 10),
                'session_activity_score': (0, 1)
            }
        }
        
        # Track if enable all sequence types
        self.enable_all_sequence_types = enable_all_sequence_types
        
        # Counter for sequences generated (for training)
        self.sequences_generated = defaultdict(int)
        
        # Store recent sequences for each server
        self.recent_sequences = defaultdict(lambda: {
            SequenceType.EVENT_TYPE: [],
            SequenceType.RISK_SCORE: [],
            SequenceType.ATTACK_PATTERN: [],
            SequenceType.SESSION_BEHAVIOR: [],
            SequenceType.AUTH_BEHAVIOR: [],
            SequenceType.SYSTEM_HEALTH: [],
            SequenceType.NETWORK_ACTIVITY: [],
            SequenceType.COMBINED: []
        })
        
        # Track last processed index for stride
        self.last_processed_index = defaultdict(int)
        
    def build_sequence(self, log) -> Dict[str, Any]:
        """
        Build sequences from a log entry
        
        Args:
            log: Log entry with metadata, features, and server ID
            
        Returns:
            Dictionary with sequences for different models
        """
        sid = log.sid
        features = log.metadata.get("features", {})
        parsed = log.metadata.get("parsed", {})
        timestamp = log.timestamp
        
        # Validate required fields
        if not features:
            return {
                "ready": False,
                "error": "No features available for sequence building",
                "sid": sid
            }
        
        # Update stateful trackers
        self._update_session_state(sid, features, parsed, timestamp)
        self._update_attack_state(sid, features)
        self._update_auth_state(sid, features)
        
        # Build different types of feature vectors
        event_type_vector = self._build_event_type_vector(features, parsed)
        risk_score_vector = self._build_risk_score_vector(features)
        attack_pattern_vector = self._build_attack_pattern_vector(sid, features)
        session_behavior_vector = self._build_session_behavior_vector(sid, features, timestamp)
        auth_behavior_vector = self._build_auth_behavior_vector(sid, features)
        system_health_vector = self._build_system_health_vector(features)
        network_activity_vector = self._build_network_activity_vector(features)
        
        # Combined vector (concatenation of important features)
        combined_vector = self._build_combined_vector(
            event_type_vector, risk_score_vector, attack_pattern_vector,
            session_behavior_vector, auth_behavior_vector, system_health_vector,
            network_activity_vector
        )
        
        # Add to sequences
        sequences = self.server_sequences[sid]
        sequences[SequenceType.EVENT_TYPE].append(event_type_vector)
        sequences[SequenceType.RISK_SCORE].append(risk_score_vector)
        sequences[SequenceType.ATTACK_PATTERN].append(attack_pattern_vector)
        sequences[SequenceType.SESSION_BEHAVIOR].append(session_behavior_vector)
        sequences[SequenceType.AUTH_BEHAVIOR].append(auth_behavior_vector)
        sequences[SequenceType.SYSTEM_HEALTH].append(system_health_vector)
        sequences[SequenceType.NETWORK_ACTIVITY].append(network_activity_vector)
        sequences[SequenceType.COMBINED].append(combined_vector)
        
        # Check stride condition
        self.last_processed_index[sid] += 1
        if self.last_processed_index[sid] % self.stride != 0:
            return {
                "ready": False,
                "reason": "Stride not met",
                "sid": sid,
                "index": self.last_processed_index[sid]
            }
        
        # Build result dictionary
        result = {
            "ready": False,
            "sid": sid,
            "timestamp": timestamp.isoformat(),
            "sequences": {}
        }
        
        # Check if we have enough data for each sequence type
        for seq_type in SequenceType:
            seq = sequences[seq_type]
            if len(seq) >= self.sequence_length:
                # Take the last sequence_length items
                sequence = list(seq)[-self.sequence_length:]
                
                # Apply normalization if configured
                if self.feature_config.get('normalize', False):
                    sequence = self._normalize_sequence(sequence, seq_type)
                
                result["sequences"][seq_type.value] = {
                    "sequence": sequence,
                    "length": len(sequence),
                    "shape": (len(sequence), len(sequence[0]) if sequence else 0)
                }
                result["ready"] = True
        
        # Store recent sequences for analytics
        if result["ready"]:
            for seq_type, seq_data in result["sequences"].items():
                self.recent_sequences[sid][SequenceType(seq_type)].append(seq_data)
                
                # Limit stored sequences
                if len(self.recent_sequences[sid][SequenceType(seq_type)]) > self.max_sequences_per_server:
                    self.recent_sequences[sid][SequenceType(seq_type)].pop(0)
            
            self.sequences_generated[sid] += 1
        
        return result
    
    def _build_event_type_vector(self, features: Dict, parsed: Dict) -> List[float]:
        """
        Build event type sequence vector
        - One-hot or encoded event types
        - Temporal patterns
        """
        event_code = features.get("event_type_code", 0)
        
        # Get additional event metadata
        is_privileged = 1 if parsed.get("user") in ["root", "admin", "cyrus", "news"] else 0
        event_severity = features.get("risk_level", 0) / 10 if "risk_level" in features else 0
        
        # Event type vector with multiple dimensions
        vector = [
            float(event_code) / 35.0,  # Normalize event type code (0-35)
            is_privileged,
            event_severity,
            features.get("is_business_hours", 0),
            features.get("is_weekend", 0)
        ]
        
        return vector
    
    def _build_risk_score_vector(self, features: Dict) -> List[float]:
        """
        Build risk score sequence vector
        - Raw risk score
        - Risk level
        - Risk components
        """
        risk_score = features.get("risk_score", 0)
        risk_level = features.get("risk_level", 0)
        
        # Extract risk components if available
        auth_risk = min(features.get("auth_failures_5min", 0) / 50, 1.0)
        attack_risk = 1.0 if features.get("anomaly_detected", 0) else 0.0
        system_risk = min(features.get("service_events_5min", 0) / 10, 1.0)
        
        vector = [
            risk_score / 100.0,  # Normalize to 0-1
            risk_level / 10.0,    # Normalize risk level
            auth_risk,
            attack_risk,
            system_risk
        ]
        
        return vector
    
    def _build_attack_pattern_vector(self, sid: str, features: Dict) -> List[float]:
        """
        Build attack pattern sequence vector
        - Attack type flags
        - Attack severity
        - Attack persistence
        """
        attack_state = self.attack_state[sid]
        
        # Get attack flags from features
        attack_flags = [
            features.get("brute_force_detected", 0),
            features.get("dictionary_attack_detected", 0),
            features.get("distributed_attack_detected", 0),
            features.get("ftp_abuse_detected", 0),
            features.get("rapid_session_detected", 0),
            features.get("suspicious_hour_detected", 0),
            features.get("rate_anomaly_detected", 0)
        ]
        
        # Calculate attack severity (sum of weighted flags)
        attack_severity = sum([
            attack_flags[0] * 0.3,  # brute force
            attack_flags[1] * 0.25, # dictionary
            attack_flags[2] * 0.35, # distributed
            attack_flags[3] * 0.2,  # ftp abuse
            attack_flags[4] * 0.15, # rapid session
            attack_flags[5] * 0.1,  # suspicious hour
            attack_flags[6] * 0.2   # rate anomaly
        ])
        
        # Attack persistence (how many recent attacks)
        recent_attacks = len(attack_state['attack_history'])
        attack_persistence = min(recent_attacks / 10, 1.0)
        
        vector = attack_flags + [attack_severity, attack_persistence]
        
        return vector
    
    def _build_session_behavior_vector(self, sid: str, features: Dict, timestamp: datetime) -> List[float]:
        """
        Build session behavior sequence vector
        - Active sessions count
        - Session durations
        - Session switching rate
        - User activity patterns
        """
        session_state = self.session_state[sid]
        
        # Active sessions
        active_sessions = len(session_state['current_sessions'])
        
        # Session duration if available
        session_duration = features.get("session_duration", 0)
        normalized_duration = min(session_duration / 3600, 24) / 24  # Normalize to 0-1 (max 24 hours)
        
        # Session switching rate
        recent_sessions = len([s for s in session_state['session_history'] 
                              if s > timestamp - timedelta(minutes=10)])
        switching_rate = min(recent_sessions / 20, 1.0)
        
        # Session activity score
        session_activity = 1.0 if active_sessions > 0 else 0.0
        
        vector = [
            active_sessions / 10.0,  # Normalize active sessions
            normalized_duration,
            switching_rate,
            session_activity,
            features.get("session_count_5min", 0) / 20.0  # Normalize session count
        ]
        
        return vector
    
    def _build_auth_behavior_vector(self, sid: str, features: Dict) -> List[float]:
        """
        Build authentication behavior sequence vector
        - Failure rates
        - Success rates
        - User diversity
        - IP diversity
        """
        auth_state = self.auth_state[sid]
        
        # Failure rate (normalized)
        failure_count = features.get("auth_failures_5min", 0)
        failure_rate = min(failure_count / 20, 1.0)
        
        # Success rate (if available)
        success_count = len(auth_state['recent_successes'])
        success_rate = min(success_count / 20, 1.0)
        
        # User diversity (unique users failing)
        unique_users = len(auth_state['user_failure_count'])
        user_diversity = min(unique_users / 10, 1.0)
        
        # IP diversity from features
        ip_diversity = features.get("unique_ips_user_5min", 0) / 10.0
        
        vector = [
            failure_rate,
            success_rate,
            user_diversity,
            ip_diversity,
            features.get("invalid_users_5min", 0) / 20.0  # Invalid user rate
        ]
        
        return vector
    
    def _build_system_health_vector(self, features: Dict) -> List[float]:
        """
        Build system health sequence vector
        - Service failures
        - Kernel warnings
        - Resource issues
        - Alert counts
        """
        service_failures = features.get("service_events_5min", 0)
        kernel_warnings = features.get("kernel_warnings_5min", 0)
        
        vector = [
            min(service_failures / 10, 1.0),
            min(kernel_warnings / 10, 1.0),
            features.get("system_alert_count_10min", 0) / 20.0,
            features.get("memory_event", 0),
            features.get("cpu_event", 0),
            features.get("disk_event", 0)
        ]
        
        return vector
    
    def _build_network_activity_vector(self, features: Dict) -> List[float]:
        """
        Build network activity sequence vector
        - FTP connections
        - SNMP packets
        - Connection rates
        """
        vector = [
            min(features.get("ftp_connections_5min", 0) / 50, 1.0),
            features.get("ftp_scanning_detected", 0),
            features.get("ftp_anonymous_count_5min", 0) / 10.0,
            features.get("other_events_5min", 0) / 20.0
        ]
        
        return vector
    
    def _build_combined_vector(self, *vectors: List[float]) -> List[float]:
        """
        Build combined vector from all sequence types
        Concatenates important features for a single LSTM model
        """
        combined = []
        
        # Add key features from each vector type
        if len(vectors) >= 1 and vectors[0]:
            combined.extend(vectors[0][:3])  # Event type: code, privileged, severity
        if len(vectors) >= 2 and vectors[1]:
            combined.extend(vectors[1][:2])  # Risk: score, level
        if len(vectors) >= 3 and vectors[2]:
            combined.extend(vectors[2][:4])  # Attack: first 4 attack flags
        if len(vectors) >= 4 and vectors[3]:
            combined.extend(vectors[3][:3])  # Session: active, duration, switching
        if len(vectors) >= 5 and vectors[4]:
            combined.extend(vectors[4][:3])  # Auth: failure rate, success rate, diversity
        if len(vectors) >= 6 and vectors[5]:
            combined.extend(vectors[5][:3])  # System: service failures, kernel warnings, alerts
        if len(vectors) >= 7 and vectors[6]:
            combined.extend(vectors[6][:2])  # Network: FTP connections, scanning
        
        return combined
    
    def _update_session_state(self, sid: str, features: Dict, parsed: Dict, timestamp: datetime):
        """Update session state tracking"""
        event_type = parsed.get("event_type", "")
        session_state = self.session_state[sid]
        
        if "session_open" in event_type:
            user = parsed.get("user", "unknown")
            session_state['current_sessions'][user] = timestamp
            session_state['session_count'] += 1
            
        elif "session_close" in event_type:
            user = parsed.get("user", "unknown")
            if user in session_state['current_sessions']:
                start_time = session_state['current_sessions'][user]
                duration = (timestamp - start_time).total_seconds()
                session_state['session_history'].append((timestamp, duration))
                del session_state['current_sessions'][user]
        
        # Clean old session history (keep last 1 hour)
        cutoff = timestamp - timedelta(hours=1)
        session_state['session_history'] = deque(
            [(t, d) for t, d in session_state['session_history'] if t > cutoff],
            maxlen=100
        )
    
    def _update_attack_state(self, sid: str, features: Dict):
        """Update attack pattern state tracking"""
        attack_state = self.attack_state[sid]
        
        # Track active attacks
        if features.get("anomaly_detected", 0):
            attack_type = features.get("anomaly_type", "unknown")
            if attack_type != "unknown":
                attack_state['active_attacks'].add(attack_type)
        
        # Clean old attack history
        if attack_state['attack_history']:
            attack_state['attack_history'].append(features.get("anomaly_detected", 0))
            if len(attack_state['attack_history']) > 100:
                attack_state['attack_history'].pop(0)
    
    def _update_auth_state(self, sid: str, features: Dict):
        """Update authentication state tracking"""
        auth_state = self.auth_state[sid]
        
        # Track failures
        failure_count = features.get("auth_failures_5min", 0)
        if failure_count > 0:
            auth_state['recent_failures'].append(failure_count)
            
            # Update user failure counts if available
            user = features.get("user", "unknown")
            if user != "unknown":
                auth_state['user_failure_count'][user] += 1
        
        # Track successes
        success_count = features.get("success_after_failure_5min", 0)
        if success_count > 0:
            auth_state['recent_successes'].append(success_count)
    
    def _normalize_sequence(self, sequence: List[List[float]], seq_type: SequenceType) -> List[List[float]]:
        """
        Normalize sequence features based on configured ranges
        """
        if not sequence:
            return sequence
        
        normalized = []
        feature_ranges = self.feature_config.get('feature_ranges', {})
        
        for vector in sequence:
            norm_vector = []
            for i, value in enumerate(vector):
                # Apply normalization based on feature position
                if seq_type == SequenceType.EVENT_TYPE and i < len(vector):
                    # Event type normalization
                    norm_val = min(max(value, 0), 1)  # Already normalized in building
                    norm_vector.append(norm_val)
                elif seq_type == SequenceType.RISK_SCORE:
                    # Risk score normalization
                    norm_val = min(max(value, 0), 1)
                    norm_vector.append(norm_val)
                elif seq_type == SequenceType.ATTACK_PATTERN:
                    # Attack pattern normalization
                    if i < 7:  # Attack flags (0-1)
                        norm_val = min(max(value, 0), 1)
                    else:  # Severity and persistence (0-1)
                        norm_val = min(max(value, 0), 1)
                    norm_vector.append(norm_val)
                else:
                    # Default: clip to [0, 1]
                    norm_val = min(max(value, 0), 1)
                    norm_vector.append(norm_val)
            
            normalized.append(norm_vector)
        
        return normalized
    
    def get_sequence_for_training(self, sid: str, sequence_type: SequenceType) -> Optional[np.ndarray]:
        """
        Get sequences ready for LSTM training
        
        Args:
            sid: Server ID
            sequence_type: Type of sequence to retrieve
            
        Returns:
            Numpy array of sequences, or None if not enough data
        """
        if sid not in self.recent_sequences:
            return None
        
        sequences = self.recent_sequences[sid].get(sequence_type, [])
        if len(sequences) < self.min_sequence_length:
            return None
        
        # Convert to numpy array for training
        sequence_data = []
        for seq_dict in sequences:
            seq = seq_dict['sequence']
            if len(seq) >= self.min_sequence_length:
                sequence_data.append(seq[-self.sequence_length:])
        
        if not sequence_data:
            return None
        
        return np.array(sequence_data, dtype=np.float32)
    
    def get_all_sequences(self, sid: str) -> Dict[str, np.ndarray]:
        """
        Get all sequence types for a server as numpy arrays
        
        Args:
            sid: Server ID
            
        Returns:
            Dictionary mapping sequence type to numpy array
        """
        result = {}
        
        for seq_type in SequenceType:
            sequences = self.get_sequence_for_training(sid, seq_type)
            if sequences is not None:
                result[seq_type.value] = sequences
        
        return result
    
    def reset_server_sequences(self, sid: str):
        """
        Reset sequences for a specific server
        
        Args:
            sid: Server ID to reset
        """
        if sid in self.server_sequences:
            del self.server_sequences[sid]
        if sid in self.combined_vectors:
            del self.combined_vectors[sid]
        if sid in self.session_state:
            del self.session_state[sid]
        if sid in self.attack_state:
            del self.attack_state[sid]
        if sid in self.auth_state:
            del self.auth_state[sid]
        if sid in self.recent_sequences:
            del self.recent_sequences[sid]
        if sid in self.last_processed_index:
            del self.last_processed_index[sid]
    
    def get_statistics(self, sid: Optional[str] = None) -> Dict:
        """
        Get sequence builder statistics
        
        Args:
            sid: Optional server ID for specific server statistics
            
        Returns:
            Dictionary with statistics
        """
        if sid:
            return {
                "sid": sid,
                "sequences_generated": self.sequences_generated.get(sid, 0),
                "active_sessions": len(self.session_state[sid]['current_sessions']),
                "active_attacks": len(self.attack_state[sid]['active_attacks']),
                "recent_sequences": {
                    seq_type.value: len(seqs) 
                    for seq_type, seqs in self.recent_sequences[sid].items()
                },
                "buffer_sizes": {
                    seq_type.value: len(seqs)
                    for seq_type, seqs in self.server_sequences[sid].items()
                }
            }
        else:
            return {
                "total_servers": len(self.server_sequences),
                "total_sequences_generated": sum(self.sequences_generated.values()),
                "servers": list(self.server_sequences.keys()),
                "sequences_per_server": {
                    sid: self.sequences_generated.get(sid, 0)
                    for sid in self.server_sequences.keys()
                }
            }
