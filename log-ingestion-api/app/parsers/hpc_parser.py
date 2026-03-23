"""
HPC Log Parser
Parses HPC (High Performance Computing) system logs into structured events.
Supports various log types including hardware events, actions, cluster filesystem events,
network events, temperature events, and switch module events.
"""

import re
from typing import Dict, Any, Optional, List
from datetime import datetime


class HPCParser:
    """
    Parser for HPC (High Performance Computing) system logs.
    Extracts structured information from raw HPC log messages.
    """
    
    def __init__(self):
        """Initialize the HPC parser."""
        pass
    
    def parse(self, message: str) -> Dict[str, Any]:
        """
        Parse a single HPC log message.
        
        Args:
            message (str): Raw log message string
            
        Returns:
            Dict[str, Any]: Parsed log entry with structured fields
        """
        if not message or not isinstance(message, str):
            return self._get_empty_result()
        
        message = message.strip()
        if not message:
            return self._get_empty_result()
        
        # Split the log line by whitespace to identify structure
        parts = message.split()
        
        if len(parts) < 5:
            return self._get_empty_result(message)
        
        # Extract LogId (first field)
        try:
            log_id = int(parts[0])
        except ValueError:
            log_id = 0
        
        # Determine the log type based on the structure
        parsed_result = self._parse_by_pattern(message, parts, log_id)
        
        return parsed_result
    
    def _parse_by_pattern(self, message: str, parts: List[str], log_id: int) -> Dict[str, Any]:
        """
        Parse the log by identifying its pattern.
        """
        # Pattern 1: Standard HPC log with node, component, state, timestamp, flag, content
        # Example: "134681 node-246 unix.hw state_change.unavailable 1077804742 1 Component State Change: ..."
        if len(parts) >= 6:
            # Try to parse timestamp as integer
            try:
                timestamp = int(parts[4])
                flag = int(parts[5])
                
                # Node is parts[1], component is parts[2], state is parts[3]
                node = parts[1]
                component = parts[2]
                state = parts[3]
                content = ' '.join(parts[6:]) if len(parts) > 6 else ''
                
                return self._build_structured_log(
                    log_id, node, component, state, timestamp, flag, content
                )
            except ValueError:
                pass
        
        # Pattern 2: Command logs with command ID (for boot_cmd, shutdown_cmd, etc.)
        # Example: "2566692 1897 boot_cmd success 1073991950 1 Command has completed successfully"
        if len(parts) >= 6:
            try:
                timestamp = int(parts[4])
                flag = int(parts[5])
                
                # In this pattern, parts[1] is command_id, parts[2] is component, parts[3] is state
                command_id = parts[1]
                component = parts[2]
                state = parts[3]
                node = parts[2]  # For command logs, node is often the component
                content = ' '.join(parts[6:]) if len(parts) > 6 else ''
                
                result = self._build_structured_log(
                    log_id, node, component, state, timestamp, flag, content
                )
                result['command_id'] = command_id
                return result
            except ValueError:
                pass
        
        # Pattern 3: Switch module logs
        # Example: "147394 Interconnect-0N00 switch_module temphigh 1129812510 1 Temperature (41C) exceeds warning threshold"
        if len(parts) >= 6 and parts[2] == 'switch_module':
            try:
                timestamp = int(parts[4])
                flag = int(parts[5])
                
                node = parts[1]
                component = parts[2]
                state = parts[3]
                content = ' '.join(parts[6:]) if len(parts) > 6 else ''
                
                return self._build_structured_log(
                    log_id, node, component, state, timestamp, flag, content
                )
            except ValueError:
                pass
        
        # Pattern 4: Node status logs
        # Example: "2567354 node-147 node status 1074098611 1 not responding"
        if len(parts) >= 6 and parts[2] in ['node', 'domain', 'tserver'] and parts[3] == 'status':
            try:
                timestamp = int(parts[4])
                flag = int(parts[5])
                
                node = parts[1]
                component = parts[2]
                state = parts[3]
                content = ' '.join(parts[6:]) if len(parts) > 6 else ''
                
                return self._build_structured_log(
                    log_id, node, component, state, timestamp, flag, content
                )
            except ValueError:
                pass
        
        # Pattern 5: Full partition status logs
        # Example: "2286759 full partition status 1061219795 -1 running"
        if len(parts) >= 5 and parts[1] == 'full' and parts[2] == 'partition' and parts[3] == 'status':
            try:
                timestamp = int(parts[4])
                flag = int(parts[5]) if len(parts) > 5 else -1
                content = ' '.join(parts[6:]) if len(parts) > 6 else ''
                
                node = 'full'
                component = 'partition'
                state = 'status'
                
                return self._build_structured_log(
                    log_id, node, component, state, timestamp, flag, content
                )
            except ValueError:
                pass
        
        # Pattern 6: Gige temperature logs
        # Example: "2559971 gige7 gige temperature 1073151998 1 normal"
        if len(parts) >= 6 and 'gige' in parts[1] and parts[2] == 'gige' and parts[3] == 'temperature':
            try:
                timestamp = int(parts[4])
                flag = int(parts[5])
                
                node = parts[1]
                component = parts[2]
                state = parts[3]
                content = ' '.join(parts[6:]) if len(parts) > 6 else ''
                
                return self._build_structured_log(
                    log_id, node, component, state, timestamp, flag, content
                )
            except ValueError:
                pass
        
        # Pattern 7: Node temperature logs
        # Example: "2552992 node-212 node temperature 1072633140 1 ambient=30"
        if len(parts) >= 6 and parts[2] == 'node' and parts[3] == 'temperature':
            try:
                timestamp = int(parts[4])
                flag = int(parts[5])
                
                node = parts[1]
                component = parts[2]
                state = parts[3]
                content = ' '.join(parts[6:]) if len(parts) > 6 else ''
                
                return self._build_structured_log(
                    log_id, node, component, state, timestamp, flag, content
                )
            except ValueError:
                pass
        
        # Pattern 8: Short format with no flag (some lines have only 6 fields)
        # Example: "2573188 node-129 unix.hw net.niff.up 1074131255 NIFF: node node-129 ..."
        if len(parts) >= 5:
            try:
                timestamp = int(parts[4])
                
                node = parts[1]
                component = parts[2]
                state = parts[3]
                content = ' '.join(parts[5:]) if len(parts) > 5 else ''
                flag = 1  # Default flag
                
                return self._build_structured_log(
                    log_id, node, component, state, timestamp, flag, content
                )
            except ValueError:
                pass
        
        # If no pattern matches, return basic structure
        return self._get_empty_result(message, log_id)
    
    def _build_structured_log(self, log_id: int, node: str, component: str, 
                              state: str, timestamp: int, flag: int, 
                              content: str) -> Dict[str, Any]:
        """
        Build structured log dictionary with all fields and metadata.
        """
        # Determine event type and severity
        event_info = self._classify_event_type(component, state, content)
        
        # Extract metadata from content
        metadata = self._extract_metadata(content)
        
        # Build the structured log
        structured_log = {
            'log_id': log_id,
            'node': node,
            'component': component,
            'state': state,
            'timestamp': timestamp,
            'timestamp_iso': datetime.fromtimestamp(timestamp).isoformat() if timestamp > 0 else None,
            'flag': flag,
            'raw_content': content,
            'event_id': event_info['event_id'],
            'event_type': event_info['event_type'],
            'severity': event_info['severity'],
            'metadata': metadata,
            'is_anomaly': self._is_anomaly(event_info['severity'], content),
            'risk_score': self._calculate_risk_score(event_info['severity'], metadata),
        }
        
        return structured_log
    
    def _classify_event_type(self, component: str, state: str, content: str) -> Dict[str, str]:
        """
        Classify the event type based on component, state, and content.
        Returns dictionary with event_id, event_type, and severity.
        """
        # Check content-based patterns
        if 'Component State Change' in content:
            return {'event_id': 'E13', 'event_type': 'component_unavailable', 'severity': 'error'}
        
        if 'Command has completed successfully' in content:
            return {'event_id': 'E12', 'event_type': 'command_success', 'severity': 'info'}
        
        if 'Command has been aborted' in content:
            return {'event_id': 'E11', 'event_type': 'command_aborted', 'severity': 'warning'}
        
        if 'Targeting domains:' in content:
            if 'child of command' in content:
                return {'event_id': 'E42', 'event_type': 'targeting_domains_range', 'severity': 'info'}
            else:
                return {'event_id': 'E43', 'event_type': 'targeting_domains_single', 'severity': 'info'}
        
        if 'ClusterFileSystem:' in content:
            if 'no server' in content:
                return {'event_id': 'E10', 'event_type': 'cluster_no_server', 'severity': 'error'}
            elif 'no longer served' in content:
                return {'event_id': 'E9', 'event_type': 'cluster_not_served', 'severity': 'error'}
        
        if 'ServerFileSystem:' in content:
            if 'is full' in content:
                return {'event_id': 'E40', 'event_type': 'fdmn_full', 'severity': 'error'}
            elif 'panic' in content:
                return {'event_id': 'E39', 'event_type': 'fdmn_panic', 'severity': 'critical'}
        
        if 'detected a failed network connection' in content:
            return {'event_id': 'E27', 'event_type': 'network_down', 'severity': 'error'}
        
        if 'detected an available network connection' in content:
            if 'via interface ee0' in content:
                return {'event_id': 'E29', 'event_type': 'network_up', 'severity': 'info'}
            elif 'via interface alt0' in content:
                return {'event_id': 'E28', 'event_type': 'network_up', 'severity': 'info'}
            elif 'via interface scip0' in content:
                return {'event_id': 'E30', 'event_type': 'network_up', 'severity': 'info'}
        
        if 'Fan speeds' in content:
            if '****' in content:
                return {'event_id': 'E17', 'event_type': 'fan_speed', 'severity': 'warning'}
            else:
                return {'event_id': 'E18', 'event_type': 'fan_speed_all', 'severity': 'info'}
        
        if 'Temperature' in content and 'exceeds warning threshold' in content:
            return {'event_id': 'E44', 'event_type': 'temperature_warning', 'severity': 'warning'}
        
        if 'psu failure' in content:
            return {'event_id': 'E35', 'event_type': 'psu_failure', 'severity': 'critical'}
        
        if 'power/control problem' in content:
            return {'event_id': 'E34', 'event_type': 'power_control_problem', 'severity': 'critical'}
        
        if 'Link error' in content:
            if 'broadcast tree' in content:
                return {'event_id': 'E22', 'event_type': 'broadcast_error', 'severity': 'error'}
            else:
                return {'event_id': 'E21', 'event_type': 'link_error', 'severity': 'error'}
        
        if 'Link in reset' in content:
            return {'event_id': 'E24', 'event_type': 'link_in_reset', 'severity': 'warning'}
        
        if 'Link ok' in content:
            return {'event_id': 'E25', 'event_type': 'link_ok', 'severity': 'info'}
        
        if 'link errors remain current' in content:
            return {'event_id': 'E23', 'event_type': 'link_errors_remain', 'severity': 'warning'}
        
        if 'Linkerror event interval expired' in content:
            return {'event_id': 'E26', 'event_type': 'linkerror_interval', 'severity': 'warning'}
        
        # Check component and state based classification
        if component == 'action':
            if state == 'start':
                if 'boot' in content:
                    return {'event_id': 'E4', 'event_type': 'boot_command', 'severity': 'info'}
                elif 'halt' in content:
                    return {'event_id': 'E19', 'event_type': 'halt_command', 'severity': 'warning'}
                elif 'wait' in content:
                    return {'event_id': 'E45', 'event_type': 'wait_command', 'severity': 'info'}
                elif 'risBoot' in content:
                    return {'event_id': 'E36', 'event_type': 'ris_boot', 'severity': 'info'}
                elif 'bootGenvmunix' in content:
                    return {'event_id': 'E6', 'event_type': 'boot_genvmunix', 'severity': 'info'}
                elif 'clusterAddMember' in content:
                    return {'event_id': 'E8', 'event_type': 'cluster_add_member', 'severity': 'info'}
            elif state == 'error':
                if 'Timed out while waiting for SRM prompt' in content:
                    return {'event_id': 'E37', 'event_type': 'ris_boot_timeout', 'severity': 'error'}
                elif 'HALT asserted' in content:
                    return {'event_id': 'E5', 'event_type': 'boot_error_halt', 'severity': 'error'}
                else:
                    return {'event_id': 'E16', 'event_type': 'command_error', 'severity': 'error'}
        
        if component == 'unix.hw':
            if 'unavailable' in state:
                return {'event_id': 'E13', 'event_type': 'component_unavailable', 'severity': 'error'}
            elif 'net.niff.down' in state:
                return {'event_id': 'E27', 'event_type': 'network_down', 'severity': 'error'}
            elif 'net.niff.up' in state:
                return {'event_id': 'E28', 'event_type': 'network_up', 'severity': 'info'}
        
        if component == 'node' and state == 'status':
            if 'not responding' in content:
                return {'event_id': 'E32', 'event_type': 'not_responding', 'severity': 'error'}
            elif 'running' in content:
                return {'event_id': 'E38', 'event_type': 'running', 'severity': 'info'}
            elif 'configured out' in content:
                return {'event_id': 'E14', 'event_type': 'configured_out', 'severity': 'warning'}
            elif 'active' in content:
                return {'event_id': 'E1', 'event_type': 'active', 'severity': 'info'}
        
        if component == 'domain' and state == 'status':
            if 'inconsistent nodesets' in content:
                return {'event_id': 'E20', 'event_type': 'inconsistent_nodesets', 'severity': 'critical'}
            elif 'not responding' in content:
                return {'event_id': 'E32', 'event_type': 'not_responding', 'severity': 'error'}
        
        if component == 'tserver' and state == 'status':
            return {'event_id': 'E33', 'event_type': 'not_responding', 'severity': 'error'}
        
        if component == 'gige' and state == 'temperature':
            if 'normal' in content:
                return {'event_id': 'E31', 'event_type': 'normal', 'severity': 'info'}
            elif 'warning' in content:
                return {'event_id': 'E46', 'event_type': 'warning', 'severity': 'warning'}
            elif 'critical' in content:
                return {'event_id': 'E15', 'event_type': 'critical', 'severity': 'critical'}
        
        if component == 'partition' and state == 'status':
            if 'running' in content:
                return {'event_id': 'E38', 'event_type': 'running', 'severity': 'info'}
            elif 'blocked' in content:
                return {'event_id': 'E3', 'event_type': 'blocked', 'severity': 'warning'}
            elif 'closing' in content:
                return {'event_id': 'E7', 'event_type': 'closing', 'severity': 'info'}
            elif 'starting' in content:
                return {'event_id': 'E41', 'event_type': 'starting', 'severity': 'info'}
        
        # Default
        return {'event_id': 'E31', 'event_type': 'normal', 'severity': 'info'}
    
    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """
        Extract additional metadata from the content string.
        """
        metadata = {}
        
        # Extract HWID from component state change logs
        hwid_match = re.search(r'HWID=(\d+)', content)
        if hwid_match:
            metadata['hwid'] = int(hwid_match.group(1))
        
        # Extract component name from state change logs
        component_match = re.search(r'Component \\042([^\\]+)\\"', content)
        if component_match:
            metadata['component_name'] = component_match.group(1)
        
        # Extract command ID
        cmd_match = re.search(r'command (\d+)', content)
        if cmd_match:
            metadata['command_id'] = int(cmd_match.group(1))
        
        # Extract temperature values
        temp_match = re.search(r'Temperature \((\d+)C\)', content)
        if temp_match:
            metadata['temperature_celsius'] = int(temp_match.group(1))
        
        # Extract ambient temperature
        ambient_match = re.search(r'ambient=(\d+)', content)
        if ambient_match:
            metadata['ambient_temperature_celsius'] = int(ambient_match.group(1))
        
        # Extract fan speeds
        fan_match = re.search(r'Fan speeds \((.+)\)', content)
        if fan_match:
            speeds = fan_match.group(1).split()
            metadata['fan_speeds'] = []
            for s in speeds:
                if s == '****':
                    metadata['fan_speeds'].append(None)
                else:
                    try:
                        metadata['fan_speeds'].append(int(s))
                    except ValueError:
                        metadata['fan_speeds'].append(None)
        
        # Extract domain information
        domain_match = re.search(r'domain (\S+)', content)
        if domain_match:
            metadata['domain'] = domain_match.group(1)
        
        # Extract storage ID
        storage_match = re.search(r'storage(\d+)', content)
        if storage_match:
            metadata['storage_id'] = storage_match.group(1)
        
        # Extract node IDs from range
        nodes_match = re.search(r'node-\[(\d+)-(\d+)\]', content)
        if nodes_match:
            metadata['node_range_start'] = int(nodes_match.group(1))
            metadata['node_range_end'] = int(nodes_match.group(2))
        
        # Extract single node ID
        single_node_match = re.search(r'node-(\d+)', content)
        if single_node_match and 'node_range' not in metadata:
            metadata['target_node'] = int(single_node_match.group(1))
        
        # Extract network information
        network_match = re.search(r'network ([\d\.]+)', content)
        if network_match:
            metadata['network'] = network_match.group(1)
        
        # Extract interface
        interface_match = re.search(r'interface (\w+)', content)
        if interface_match:
            metadata['interface'] = interface_match.group(1)
        
        # Extract error message
        error_match = re.search(r'Error:\s*(.+?)(?:$|\.)', content)
        if error_match:
            metadata['error_message'] = error_match.group(1).strip()
        
        return metadata
    
    def _is_anomaly(self, severity: str, content: str) -> bool:
        """
        Determine if an event is anomalous based on severity and content.
        """
        # Critical and error events are considered anomalies
        if severity in ['critical', 'error']:
            return True
        
        # Specific patterns that indicate anomalies
        anomaly_patterns = [
            r'failed',
            r'error',
            r'panic',
            r'unavailable',
            r'not responding',
            r'full',
            r'critical',
            r'warning',
            r'psu failure',
            r'link error',
            r'inconsistent',
            r'no server',
            r'abort',
            r'temperature.*exceeds',
        ]
        
        content_lower = content.lower()
        for pattern in anomaly_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _calculate_risk_score(self, severity: str, metadata: Dict[str, Any]) -> int:
        """
        Calculate risk score based on severity and metadata.
        Risk score ranges from 0 (lowest) to 100 (highest).
        """
        severity_scores = {
            'info': 0,
            'warning': 25,
            'error': 50,
            'critical': 75,
        }
        
        base_score = severity_scores.get(severity, 0)
        
        # Adjust based on metadata
        if 'temperature_celsius' in metadata:
            temp = metadata['temperature_celsius']
            if temp > 45:
                base_score += 25
            elif temp > 40:
                base_score += 15
            elif temp > 35:
                base_score += 5
        
        if 'ambient_temperature_celsius' in metadata:
            temp = metadata['ambient_temperature_celsius']
            if temp > 35:
                base_score += 20
            elif temp > 30:
                base_score += 10
        
        if 'fan_speeds' in metadata:
            # Check for any fan speed that's abnormal (too low or too high)
            speeds = metadata['fan_speeds']
            for speed in speeds:
                if speed and (speed < 2000 or speed > 5000):
                    base_score += 15
                    break
        
        # Cap at 100
        return min(base_score, 100)
    
    def _get_empty_result(self, message: str = '', log_id: int = 0) -> Dict[str, Any]:
        """
        Return empty result structure for unparseable logs.
        """
        return {
            'log_id': log_id,
            'node': 'unknown',
            'component': 'unknown',
            'state': 'unknown',
            'timestamp': 0,
            'timestamp_iso': None,
            'flag': 0,
            'raw_content': message,
            'event_id': 'E0',
            'event_type': 'unknown',
            'severity': 'info',
            'metadata': {},
            'is_anomaly': False,
            'risk_score': 0,
        }
    
    def parse_batch(self, messages: List[str]) -> List[Dict[str, Any]]:
        """
        Parse multiple HPC log messages.
        
        Args:
            messages (List[str]): List of raw log messages
            
        Returns:
            List[Dict[str, Any]]: List of parsed log entries
        """
        return [self.parse(msg) for msg in messages if msg]
