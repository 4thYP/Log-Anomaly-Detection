"""
HPC Log Feature Extractor
Extracts behavioral features from parsed HPC logs for anomaly detection and analysis.
Features include event categorization, metadata extraction, risk scoring, and temporal patterns.
"""

from typing import Dict, Any, List
from datetime import datetime


class HPCFeatureExtractor:
    """
    Feature extractor for HPC (High Performance Computing) system logs.
    Extracts various features from parsed logs for LSTM-based anomaly detection.
    """
    
    def __init__(self):
        """Initialize the feature extractor."""
        # Track state for features that require history across multiple calls
        self.previous_log = None
        self.event_sequence = []
        self.max_sequence_length = 100
        self.node_error_counts = {}
        self.component_error_counts = {}
        
    def extract(self, log) -> Dict:
        """
        Extract features from a single parsed log entry.
        
        Args:
            log (Dict[str, Any]): Parsed log entry from HPCParser
            
        Returns:
            Dict[str, Any]: Dictionary containing all extracted features
        """
        # Get the parsed metadata from the log
        parsed = log.metadata.get("parsed", {})
        
        # Initialize features dictionary
        features = {}
        
        # Extract basic log features
        features.update(self._extract_basic_features(log))
        
        # Extract event classification features
        features.update(self._extract_event_features(log))
        
        # Extract severity and risk features
        features.update(self._extract_severity_features(log))
        
        # Extract temporal features (requires previous log)
        features.update(self._extract_temporal_features(log))
        
        # Extract node-specific features
        features.update(self._extract_node_features(log))
        
        # Extract component-specific features
        features.update(self._extract_component_features(log))
        
        # Extract hardware-related features (temperature, fan speeds, etc.)
        features.update(self._extract_hardware_features(log, parsed))
        
        # Extract network-related features
        features.update(self._extract_network_features(log))
        
        # Extract cluster filesystem features
        features.update(self._extract_filesystem_features(log, parsed))
        
        # Extract command execution features
        features.update(self._extract_command_features(log, parsed))
        
        # Extract content-based features
        features.update(self._extract_content_features(log))
        
        # Update state for next log
        self._update_state(log)
        
        return features
    
    def _extract_basic_features(self, log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract basic log features like log_id, timestamp, etc.
        """
        timestamp = log.get('timestamp', 0)
        timestamp_iso = log.get('timestamp_iso', '')
        
        # Convert timestamp to datetime for time-based features
        dt = None
        if timestamp > 0:
            dt = datetime.fromtimestamp(timestamp)
        
        features = {
            'log_id': log.get('log_id', 0),
            'timestamp': timestamp,
            'timestamp_iso': timestamp_iso,
            'timestamp_hour': dt.hour if dt else -1,
            'timestamp_day': dt.weekday() if dt else -1,
            'timestamp_month': dt.month if dt else -1,
            'flag': log.get('flag', 0),
            'has_timestamp': 1 if timestamp > 0 else 0,
        }
        
        return features
    
    def _extract_event_features(self, log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract event classification features.
        """
        event_id = log.get('event_id', 'E0')
        event_type = log.get('event_type', 'unknown')
        
        # Encode event type as numerical code for LSTM
        event_code = self._encode_event_type(event_type)
        
        # Track event in sequence
        self.event_sequence.append(event_code)
        if len(self.event_sequence) > self.max_sequence_length:
            self.event_sequence.pop(0)
        
        features = {
            'event_id': event_id,
            'event_type': event_type,
            'event_type_code': event_code,
            'event_sequence_position': len(self.event_sequence),
            'event_frequency_in_sequence': self.event_sequence.count(event_code) / max(len(self.event_sequence), 1),
        }
        
        return features
    
    def _extract_severity_features(self, log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract severity and risk-related features.
        """
        severity = log.get('severity', 'info')
        risk_score = log.get('risk_score', 0)
        is_anomaly = log.get('is_anomaly', False)
        
        # Convert severity to numerical code
        severity_code = self._encode_severity(severity)
        
        features = {
            'severity': severity,
            'severity_code': severity_code,
            'risk_score': risk_score,
            'is_anomaly': 1 if is_anomaly else 0,
            'risk_level': self._get_risk_level(risk_score),
        }
        
        return features
    
    def _extract_temporal_features(self, log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract temporal features based on comparison with previous log.
        """
        features = {
            'time_since_last_event': -1,
            'event_burst_indicator': 0,
            'is_consecutive_anomaly': 0,
        }
        
        if self.previous_log:
            current_time = log.get('timestamp', 0)
            previous_time = self.previous_log.get('timestamp', 0)
            
            if current_time > 0 and previous_time > 0:
                time_diff = current_time - previous_time
                features['time_since_last_event'] = time_diff
                
                # Detect bursts (events within 5 seconds of each other)
                if time_diff < 5:
                    features['event_burst_indicator'] = 1
                
                # Check if this is a consecutive anomaly
                prev_anomaly = self.previous_log.get('is_anomaly', False)
                current_anomaly = log.get('is_anomaly', False)
                if prev_anomaly and current_anomaly:
                    features['is_consecutive_anomaly'] = 1
        
        return features
    
    def _extract_node_features(self, log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract node-specific features.
        """
        node = log.get('node', 'unknown')
        
        # Track node error counts
        severity = log.get('severity', 'info')
        if severity in ['error', 'critical']:
            self.node_error_counts[node] = self.node_error_counts.get(node, 0) + 1
        
        # Determine node type
        node_type = self._get_node_type(node)
        node_importance = self._get_node_importance(node)
        
        features = {
            'node': node,
            'node_type': node_type,
            'node_importance': node_importance,
            'is_control_node': 1 if node.startswith('node-D') else 0,
            'is_interconnect': 1 if node.startswith('Interconnect') else 0,
            'is_switch_module': 1 if 'switch_module' in node else 0,
            'node_error_count': self.node_error_counts.get(node, 0),
        }
        
        return features
    
    def _extract_component_features(self, log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract component-specific features.
        """
        component = log.get('component', 'unknown')
        
        # Track component error counts
        severity = log.get('severity', 'info')
        if severity in ['error', 'critical']:
            self.component_error_counts[component] = self.component_error_counts.get(component, 0) + 1
        
        # Component categories
        component_category = self._get_component_category(component)
        component_importance = self._get_component_importance(component)
        
        features = {
            'component': component,
            'component_category': component_category,
            'component_importance': component_importance,
            'component_error_count': self.component_error_counts.get(component, 0),
        }
        
        return features
    
    def _extract_hardware_features(self, log: Dict[str, Any], parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract hardware-related features like temperature, fan speeds, power, etc.
        """
        features = {
            'has_temperature': 0,
            'temperature_celsius': 0,
            'has_ambient_temperature': 0,
            'ambient_temperature_celsius': 0,
            'has_fan_speeds': 0,
            'fan_speed_min': 0,
            'fan_speed_max': 0,
            'fan_speed_avg': 0,
            'has_hwid': 0,
            'hwid': 0,
            'is_psu_failure': 0,
            'is_power_problem': 0,
        }
        
        # Extract temperature
        if 'temperature_celsius' in parsed:
            features['has_temperature'] = 1
            features['temperature_celsius'] = parsed['temperature_celsius']
        
        # Extract ambient temperature
        if 'ambient_temperature_celsius' in parsed:
            features['has_ambient_temperature'] = 1
            features['ambient_temperature_celsius'] = parsed['ambient_temperature_celsius']
        
        # Extract fan speeds
        if 'fan_speeds' in parsed and parsed['fan_speeds']:
            speeds = [s for s in parsed['fan_speeds'] if s is not None]
            if speeds:
                features['has_fan_speeds'] = 1
                features['fan_speed_min'] = min(speeds)
                features['fan_speed_max'] = max(speeds)
                features['fan_speed_avg'] = sum(speeds) / len(speeds)
        
        # Extract HWID
        if 'hwid' in parsed:
            features['has_hwid'] = 1
            features['hwid'] = parsed['hwid']
        
        # Check for hardware failures
        event_type = log.get('event_type', '')
        if event_type == 'psu_failure':
            features['is_psu_failure'] = 1
        if event_type == 'power_control_problem':
            features['is_power_problem'] = 1
        
        return features
    
    def _extract_network_features(self, log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract network-related features.
        """
        event_type = log.get('event_type', '')
        metadata = log.get('metadata', {})
        
        features = {
            'is_network_event': 0,
            'network_event_type': 'none',
            'has_network_address': 0,
            'network_address': '',
            'has_interface': 0,
            'interface': '',
            'is_link_error': 0,
            'is_link_ok': 0,
            'is_network_up': 0,
            'is_network_down': 0,
        }
        
        # Check for network events
        network_event_types = ['network_up', 'network_down', 'link_error', 'link_ok', 'link_in_reset']
        if event_type in network_event_types:
            features['is_network_event'] = 1
            features['network_event_type'] = event_type
        
        # Extract network address
        if 'network' in metadata:
            features['has_network_address'] = 1
            features['network_address'] = metadata['network']
        
        # Extract interface
        if 'interface' in metadata:
            features['has_interface'] = 1
            features['interface'] = metadata['interface']
        
        # Specific network status flags
        if event_type == 'link_error':
            features['is_link_error'] = 1
        elif event_type == 'link_ok':
            features['is_link_ok'] = 1
        elif event_type == 'network_up':
            features['is_network_up'] = 1
        elif event_type == 'network_down':
            features['is_network_down'] = 1
        
        return features
    
    def _extract_filesystem_features(self, log: Dict[str, Any], parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract cluster filesystem-related features.
        """
        event_type = log.get('event_type', '')
        
        features = {
            'is_filesystem_event': 0,
            'filesystem_event_type': 'none',
            'has_domain': 0,
            'domain': '',
            'has_storage_id': 0,
            'storage_id': '',
            'is_fs_full': 0,
            'is_fs_panic': 0,
            'is_fs_no_server': 0,
            'is_fs_not_served': 0,
        }
        
        # Check for filesystem events
        fs_event_types = ['fdmn_full', 'fdmn_panic', 'cluster_no_server', 'cluster_not_served']
        if event_type in fs_event_types:
            features['is_filesystem_event'] = 1
            features['filesystem_event_type'] = event_type
        
        # Extract domain
        if 'domain' in parsed:
            features['has_domain'] = 1
            features['domain'] = parsed['domain']
        
        # Extract storage ID
        if 'storage_id' in parsed:
            features['has_storage_id'] = 1
            features['storage_id'] = parsed['storage_id']
        
        # Specific filesystem status flags
        if event_type == 'fdmn_full':
            features['is_fs_full'] = 1
        elif event_type == 'fdmn_panic':
            features['is_fs_panic'] = 1
        elif event_type == 'cluster_no_server':
            features['is_fs_no_server'] = 1
        elif event_type == 'cluster_not_served':
            features['is_fs_not_served'] = 1
        
        return features
    
    def _extract_command_features(self, log: Dict[str, Any], parsed: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract command execution features.
        """
        event_type = log.get('event_type', '')
        
        features = {
            'is_command_event': 0,
            'command_event_type': 'none',
            'has_command_id': 0,
            'command_id': 0,
            'has_node_range': 0,
            'node_range_start': 0,
            'node_range_end': 0,
            'has_target_node': 0,
            'target_node': 0,
            'is_command_success': 0,
            'is_command_error': 0,
            'is_command_abort': 0,
        }
        
        # Check for command events
        cmd_event_types = ['command_success', 'command_error', 'command_aborted', 
                          'boot_command', 'halt_command', 'wait_command', 
                          'ris_boot', 'boot_genvmunix', 'cluster_add_member',
                          'targeting_domains_range', 'targeting_domains_single']
        
        if event_type in cmd_event_types:
            features['is_command_event'] = 1
            features['command_event_type'] = event_type
        
        # Extract command ID
        if 'command_id' in parsed:
            features['has_command_id'] = 1
            features['command_id'] = parsed['command_id']
        
        # Extract node range
        if 'node_range_start' in parsed and 'node_range_end' in parsed:
            features['has_node_range'] = 1
            features['node_range_start'] = parsed['node_range_start']
            features['node_range_end'] = parsed['node_range_end']
        
        # Extract target node
        if 'target_node' in parsed:
            features['has_target_node'] = 1
            features['target_node'] = parsed['target_node']
        
        # Specific command status flags
        if event_type == 'command_success':
            features['is_command_success'] = 1
        elif event_type == 'command_error':
            features['is_command_error'] = 1
        elif event_type == 'command_aborted':
            features['is_command_abort'] = 1
        
        return features
    
    def _extract_content_features(self, log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract features from the raw content.
        """
        raw_content = log.get('raw_content', '')
        
        features = {
            'content_length': len(raw_content),
            'has_error_keyword': 0,
            'has_failure_keyword': 0,
            'has_timeout_keyword': 0,
            'special_char_count': 0,
            'numeric_count': 0,
        }
        
        # Count special characters
        features['special_char_count'] = sum(1 for c in raw_content if not c.isalnum() and not c.isspace())
        
        # Count numeric characters
        features['numeric_count'] = sum(1 for c in raw_content if c.isdigit())
        
        # Check for keywords
        content_lower = raw_content.lower()
        
        if any(keyword in content_lower for keyword in ['error', 'exception', 'failed']):
            features['has_error_keyword'] = 1
        
        if any(keyword in content_lower for keyword in ['failure', 'fail', 'crash', 'panic']):
            features['has_failure_keyword'] = 1
        
        if any(keyword in content_lower for keyword in ['timeout', 'timed out', 'hung']):
            features['has_timeout_keyword'] = 1
        
        return features
    
    def _update_state(self, log: Dict[str, Any]) -> None:
        """
        Update internal state with the current log for future feature extraction.
        """
        self.previous_log = log
    
    def _encode_event_type(self, event_type: str) -> int:
        """
        Encode event type as numerical code for LSTM model.
        """
        event_codes = {
            'normal': 0,
            'running': 1,
            'not_responding': 2,
            'configured_out': 3,
            'active': 4,
            'component_unavailable': 5,
            'network_down': 6,
            'network_up': 7,
            'link_error': 8,
            'link_ok': 9,
            'link_in_reset': 10,
            'link_errors_remain': 11,
            'broadcast_error': 12,
            'linkerror_interval': 13,
            'temperature_warning': 14,
            'warning': 15,
            'critical': 16,
            'fan_speed': 17,
            'fan_speed_all': 18,
            'psu_failure': 19,
            'power_control_problem': 20,
            'command_success': 21,
            'command_error': 22,
            'command_aborted': 23,
            'boot_command': 24,
            'halt_command': 25,
            'wait_command': 26,
            'ris_boot': 27,
            'ris_boot_timeout': 28,
            'boot_error_halt': 29,
            'boot_genvmunix': 30,
            'cluster_add_member': 31,
            'targeting_domains_range': 32,
            'targeting_domains_single': 33,
            'cluster_no_server': 34,
            'cluster_not_served': 35,
            'fdmn_full': 36,
            'fdmn_panic': 37,
            'inconsistent_nodesets': 38,
            'starting': 39,
            'closing': 40,
            'blocked': 41,
            'unknown': 99,
        }
        
        return event_codes.get(event_type, 99)
    
    def _encode_severity(self, severity: str) -> int:
        """
        Encode severity as numerical code.
        """
        severity_codes = {
            'info': 0,
            'warning': 1,
            'error': 2,
            'critical': 3,
        }
        return severity_codes.get(severity, 0)
    
    def _get_risk_level(self, risk_score: int) -> str:
        """
        Get risk level string from risk score.
        """
        if risk_score >= 75:
            return 'critical'
        elif risk_score >= 50:
            return 'high'
        elif risk_score >= 25:
            return 'medium'
        elif risk_score > 0:
            return 'low'
        else:
            return 'none'
    
    def _get_node_type(self, node: str) -> str:
        """
        Determine the type of node.
        """
        if not node or node == 'unknown':
            return 'unknown'
        
        if node.startswith('node-D'):
            return 'domain_controller'
        elif node.startswith('node-'):
            return 'compute_node'
        elif node.startswith('Interconnect'):
            return 'interconnect'
        elif 'switch_module' in node:
            return 'switch_module'
        elif node == 'full':
            return 'partition'
        elif node.startswith('gige'):
            return 'network_interface'
        else:
            return 'other'
    
    def _get_node_importance(self, node: str) -> float:
        """
        Get importance weight for a node (0-1 scale).
        """
        if not node:
            return 0.5
        
        if node.startswith('node-D'):
            return 1.0  # Domain controllers are most important
        elif node.startswith('Interconnect'):
            return 0.9  # Interconnect components are very important
        elif 'switch_module' in node:
            return 0.8
        elif node.startswith('node-'):
            return 0.6
        else:
            return 0.5
    
    def _get_component_category(self, component: str) -> str:
        """
        Get the category of a component.
        """
        if not component:
            return 'unknown'
        
        if component == 'unix.hw':
            return 'hardware'
        elif component == 'action':
            return 'system_action'
        elif component == 'boot_cmd':
            return 'boot_command'
        elif component == 'shutdown_cmd':
            return 'shutdown_command'
        elif component == 'clusterfilesystem':
            return 'filesystem'
        elif component == 'switch_module':
            return 'network'
        elif component == 'gige':
            return 'network_interface'
        elif component == 'node':
            return 'node_status'
        elif component == 'domain':
            return 'domain_status'
        elif component == 'tserver':
            return 'server'
        elif component == 'partition':
            return 'partition_status'
        else:
            return 'other'
    
    def _get_component_importance(self, component: str) -> float:
        """
        Get importance weight for a component (0-1 scale).
        """
        if not component:
            return 0.5
        
        important_components = {
            'unix.hw': 0.9,
            'clusterfilesystem': 1.0,
            'switch_module': 0.8,
            'boot_cmd': 0.7,
            'domain': 0.9,
            'node': 0.6,
        }
        
        return important_components.get(component, 0.5)
    
    def extract_batch(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract features from a batch of parsed logs.
        
        Args:
            logs (List[Dict[str, Any]]): List of parsed log entries
            
        Returns:
            List[Dict[str, Any]]: List of feature dictionaries
        """
        # Reset state for batch processing
        self.previous_log = None
        self.event_sequence = []
        self.node_error_counts = {}
        self.component_error_counts = {}
        
        features_list = []
        for log in logs:
            features = self.extract(log)
            features_list.append(features)
        
        return features_list
