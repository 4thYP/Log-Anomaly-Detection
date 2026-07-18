"""
HPC (High-Performance Computing) Cluster Log Parser

This parser handles logs from HPC cluster systems, including:
- Hardware state changes (unix.hw component)
- System actions (boot, halt, cluster operations)
- Network/link events
- Resource management events

Format:
  <LogId> <Node> <Component> <State> <Timestamp> <Flag> <Message>

Example:
  2575909 node-162 action start 1074178193 1 boot  (command 1911)

The parser extracts structured data into the unified ParsedLogEvent schema.
"""

import re
from typing import Dict, Optional
from app.parsers.base_parser import BaseParser
from app.parsers.log_event_schema import ParsedLogEvent, EventGroup, template_id_from_csv


class HPCParser(BaseParser):
    """
    Parses HPC cluster logs into unified ParsedLogEvent schema.
    
    State model: Maintains per-sid state for stateful operations (actions).
    Event types: component states, lifecycle actions, network events.
    """

    def __init__(self):
        # Template mapping from logs (E1-E46)
        self.templates = {
            "E1": ("active", "Component is active"),
            "E2": ("ambient", "Ambient temperature reading"),
            "E3": ("blocked", "Component is blocked"),
            "E4": ("boot", "boot  (command <*>)"),
            "E5": ("boot_error", "boot (command <*>) Error: HALT asserted"),
            "E6": ("bootgenvmunix", "bootGenvmunix  (command <*>)"),
            "E8": ("clusterAddMember", "clusterAddMember  (command <*>)"),
            "E11": ("command_aborted", "Command has been aborted"),
            "E12": ("command_completed", "Command has completed successfully"),
            "E13": ("component_unavailable", "Component State Change: Component <*> is in the unavailable state (HWID=<*>)"),
            "E14": ("configured_out", "configured out"),
            "E15": ("critical", "Component is critical"),
            "E16": ("failed_subcommands", "Failed subcommands <*>"),
            "E17": ("fan_status", "Fan speeds"),
            "E18": ("fan_status", "Fan speeds"),
            "E19": ("halt", "halt  (command <*>)"),
            "E20": ("inconsistent_nodesets", "inconsistent nodesets"),
            "E21": ("link_error", "Link error"),
            "E22": ("link_error_broadcast", "Link error on broadcast tree"),
            "E23": ("link_errors_current", "link errors remain current"),
            "E24": ("link_reset", "Link in reset"),
            "E25": ("link_ok", "Link ok"),
            "E26": ("link_error_interval", "Linkerror event interval expired"),
            "E27": ("network_connection_failed", "NIFF: node <*> detected a failed network connection on network <*> via interface alt0"),
            "E28": ("network_connection_available", "NIFF: node <*> has detected an available network connection on network <*> via interface alt0"),
            "E29": ("network_connection_available", "NIFF: node <*> has detected an available network connection on network <*> via interface ee0"),
            "E30": ("network_connection_available", "NIFF: node <*> has detected an available network connection on network <*> via interface scip0"),
            "E31": ("normal", "normal"),
            "E32": ("not_responding", "not responding"),
            "E33": ("not_responding", "not-responding"),
            "E34": ("power_control_problem", "power/control problem"),
            "E35": ("power_failure", "psu failure"),
            "E36": ("risboot", "risBoot  (command <*>)"),
            "E37": ("risboot_error", "risBoot (command <*>) Error: Timed out"),
            "E38": ("running", "running"),
            "E39": ("filesystem_panic", "ServerFileSystem: An ServerFileSystem domain panic has occurred on <*>"),
            "E40": ("filesystem_full", "ServerFileSystem: ServerFileSystem domain <*> is full"),
            "E41": ("starting", "starting"),
            "E42": ("targeting_domains", "Targeting domains"),
            "E43": ("targeting_domains", "Targeting domains"),
            "E44": ("temperature_warning", "Temperature (<*>C) exceeds warning threshold"),
            "E45": ("wait", "wait  (command <*>)"),
            "E46": ("warning", "warning"),
        }

    def parse(self, message: str) -> Dict:
        """
        Parse an HPC log line into structured ParsedLogEvent.
        
        Format: <LogId> <Node> <Component> <State> <Timestamp> <Flag> <Message>
        
        Args:
            message: Raw log line
            
        Returns:
            Dict matching ParsedLogEvent schema
        """
        try:
            # Split header fields
            parts = message.split(None, 6)  # Split into max 7 parts
            
            if len(parts) < 7:
                return self._unknown_event(message)
            
            log_id = parts[0]
            node = parts[1]
            component = parts[2]
            state = parts[3]
            timestamp_str = parts[4]
            flag = parts[5]
            message_content = parts[6]
            
            # Parse timestamp
            try:
                timestamp_int = int(timestamp_str)
                from datetime import datetime
                timestamp_iso = datetime.utcfromtimestamp(timestamp_int).isoformat()
            except (ValueError, OSError):
                timestamp_iso = None
            
            # Unescape component names (octal \042 = quote, \<octal> = char)
            message_content = self._unescape_octal(message_content)
            
            # Route based on component and state
            if component == "unix.hw":
                return self._parse_hardware_state(
                    node, component, state, timestamp_iso, message_content, log_id, flag
                )
            elif component == "action":
                return self._parse_action_event(
                    node, component, state, timestamp_iso, message_content, log_id, flag
                )
            else:
                # Unknown component
                return self._unknown_event(message)
                
        except Exception:
            return self._unknown_event(message)

    def _parse_hardware_state(self, node: str, component: str, state: str, timestamp: Optional[str], 
                               message: str, log_id: str, flag: str) -> Dict:
        """Parse unix.hw (hardware state) events."""
        
        # E13 pattern: Component State Change
        if "Component State Change" in message and "unavailable" in message:
            # E13: Component State Change: Component <name> is in the unavailable state (HWID=<id>)
            match = re.search(r"Component \042([^\042]+)\042 is in the unavailable state \(HWID=(\d+)\)", message)
            if match:
                component_name = match.group(1)
                hwid = match.group(2)
                return ParsedLogEvent(
                    event_type="component_unavailable",
                    event_group=EventGroup.ERROR,
                    component=component,
                    template="Component State Change: Component <*> is in the unavailable state (HWID=<*>)",
                    template_id=13,
                    timestamp=timestamp,
                    status="unavailable",
                    metadata={
                        "node": node,
                        "log_id": log_id,
                        "component_name": component_name,
                        "hwid": hwid,
                        "flag": flag,
                        "raw_state": state,
                    }
                ).__dict__
        
        # E1: active
        if message.strip() == "active":
            return ParsedLogEvent(
                event_type="component_active",
                event_group=EventGroup.SYSTEM,
                component=component,
                template="active",
                template_id=1,
                timestamp=timestamp,
                status="active",
                metadata={"node": node, "log_id": log_id, "flag": flag, "raw_state": state}
            ).__dict__
        
        # E3: blocked
        if message.strip() == "blocked":
            return ParsedLogEvent(
                event_type="component_blocked",
                event_group=EventGroup.ERROR,
                component=component,
                template="blocked",
                template_id=3,
                timestamp=timestamp,
                status="blocked",
                metadata={"node": node, "log_id": log_id, "flag": flag, "raw_state": state}
            ).__dict__
        
        # E15: critical
        if message.strip() == "critical":
            return ParsedLogEvent(
                event_type="component_critical",
                event_group=EventGroup.ERROR,
                component=component,
                template="critical",
                template_id=15,
                timestamp=timestamp,
                status="critical",
                metadata={"node": node, "log_id": log_id, "flag": flag, "raw_state": state}
            ).__dict__
        
        # E31: normal
        if message.strip() == "normal":
            return ParsedLogEvent(
                event_type="component_normal",
                event_group=EventGroup.SYSTEM,
                component=component,
                template="normal",
                template_id=31,
                timestamp=timestamp,
                status="normal",
                metadata={"node": node, "log_id": log_id, "flag": flag, "raw_state": state}
            ).__dict__
        
        # E32/E33: not responding
        if message.strip() in ["not responding", "not-responding"]:
            template_id = 32 if "responding" in message else 33
            return ParsedLogEvent(
                event_type="component_not_responding",
                event_group=EventGroup.ERROR,
                component=component,
                template="not responding",
                template_id=template_id,
                timestamp=timestamp,
                status="not_responding",
                metadata={"node": node, "log_id": log_id, "flag": flag, "raw_state": state}
            ).__dict__
        
        # E38: running
        if message.strip() == "running":
            return ParsedLogEvent(
                event_type="component_running",
                event_group=EventGroup.SYSTEM,
                component=component,
                template="running",
                template_id=38,
                timestamp=timestamp,
                status="running",
                metadata={"node": node, "log_id": log_id, "flag": flag, "raw_state": state}
            ).__dict__
        
        # Fallback
        return self._unknown_event(f"{node} {component} {state} {message}")

    def _parse_action_event(self, node: str, component: str, state: str, timestamp: Optional[str],
                            message: str, log_id: str, flag: str) -> Dict:
        """Parse action (lifecycle) events."""
        
        # E4: boot  (command <*>)
        boot_match = re.search(r"boot\s+\(command (\d+)\)", message)
        if boot_match:
            command_id = boot_match.group(1)
            return ParsedLogEvent(
                event_type="boot_started",
                event_group=EventGroup.SERVICE,
                component=component,
                template="boot  (command <*>)",
                template_id=4,
                timestamp=timestamp,
                status="started",
                metadata={
                    "node": node,
                    "log_id": log_id,
                    "command_id": command_id,
                    "flag": flag,
                    "action_type": "boot"
                }
            ).__dict__
        
        # E19: halt  (command <*>)
        halt_match = re.search(r"halt\s+\(command (\d+)\)", message)
        if halt_match:
            command_id = halt_match.group(1)
            return ParsedLogEvent(
                event_type="halt_started",
                event_group=EventGroup.SERVICE,
                component=component,
                template="halt  (command <*>)",
                template_id=19,
                timestamp=timestamp,
                status="started",
                metadata={
                    "node": node,
                    "log_id": log_id,
                    "command_id": command_id,
                    "flag": flag,
                    "action_type": "halt"
                }
            ).__dict__
        
        # E45: wait  (command <*>)
        wait_match = re.search(r"wait\s+\(command (\d+)\)", message)
        if wait_match:
            command_id = wait_match.group(1)
            return ParsedLogEvent(
                event_type="wait_started",
                event_group=EventGroup.SERVICE,
                component=component,
                template="wait  (command <*>)",
                template_id=45,
                timestamp=timestamp,
                status="started",
                metadata={
                    "node": node,
                    "log_id": log_id,
                    "command_id": command_id,
                    "flag": flag,
                    "action_type": "wait"
                }
            ).__dict__
        
        # E36: risBoot  (command <*>)
        risboot_match = re.search(r"risBoot\s+\(command (\d+)\)", message)
        if risboot_match:
            command_id = risboot_match.group(1)
            return ParsedLogEvent(
                event_type="risboot_started",
                event_group=EventGroup.SERVICE,
                component=component,
                template="risBoot  (command <*>)",
                template_id=36,
                timestamp=timestamp,
                status="started",
                metadata={
                    "node": node,
                    "log_id": log_id,
                    "command_id": command_id,
                    "flag": flag,
                    "action_type": "risboot"
                }
            ).__dict__
        
        # E6: bootGenvmunix  (command <*>)
        bootvmunix_match = re.search(r"bootGenvmunix\s+\(command (\d+)\)", message)
        if bootvmunix_match:
            command_id = bootvmunix_match.group(1)
            return ParsedLogEvent(
                event_type="bootvmunix_started",
                event_group=EventGroup.SERVICE,
                component=component,
                template="bootGenvmunix  (command <*>)",
                template_id=6,
                timestamp=timestamp,
                status="started",
                metadata={
                    "node": node,
                    "log_id": log_id,
                    "command_id": command_id,
                    "flag": flag,
                    "action_type": "bootvmunix"
                }
            ).__dict__
        
        # E8: clusterAddMember  (command <*>)
        cluster_match = re.search(r"clusterAddMember\s+\(command (\d+)\)", message)
        if cluster_match:
            command_id = cluster_match.group(1)
            return ParsedLogEvent(
                event_type="cluster_add_member",
                event_group=EventGroup.SERVICE,
                component=component,
                template="clusterAddMember  (command <*>)",
                template_id=8,
                timestamp=timestamp,
                status="started",
                metadata={
                    "node": node,
                    "log_id": log_id,
                    "command_id": command_id,
                    "flag": flag,
                    "action_type": "cluster_add_member"
                }
            ).__dict__
        
        # E12: Command has completed successfully
        if "Command has completed successfully" in message:
            return ParsedLogEvent(
                event_type="command_completed_success",
                event_group=EventGroup.SERVICE,
                component=component,
                template="Command has completed successfully",
                template_id=12,
                timestamp=timestamp,
                status="success",
                metadata={"node": node, "log_id": log_id, "flag": flag}
            ).__dict__
        
        # E11: Command has been aborted
        if "Command has been aborted" in message:
            return ParsedLogEvent(
                event_type="command_aborted",
                event_group=EventGroup.ERROR,
                component=component,
                template="Command has been aborted",
                template_id=11,
                timestamp=timestamp,
                status="aborted",
                metadata={"node": node, "log_id": log_id, "flag": flag}
            ).__dict__
        
        # Fallback
        return self._unknown_event(f"{node} {component} {state} {message}")

    def _unescape_octal(self, text: str) -> str:
        """Unescape octal sequences like \\042 (quote), \\012 (newline), etc."""
        def replace_octal(match):
            octal_str = match.group(1)
            try:
                char_code = int(octal_str, 8)
                return chr(char_code)
            except (ValueError, OverflowError):
                return match.group(0)
        
        return re.sub(r'\\(\d{3})', replace_octal, text)

    def _unknown_event(self, message: str) -> Dict:
        """Handle unknown or unparseable log lines."""
        return ParsedLogEvent(
            event_type="unknown",
            event_group=EventGroup.SYSTEM,
            component="unknown",
            template=None,
            template_id=None,
            timestamp=None,
            status="unknown",
            metadata={
                "raw_message": message,
                "parsed_successfully": False
            }
        ).__dict__
