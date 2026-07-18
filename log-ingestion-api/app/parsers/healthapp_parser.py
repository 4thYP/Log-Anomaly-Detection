"""
HealthApp Log Parser - Fitness/Health tracking app logs

This parser handles logs from Huawei HealthApp (or similar fitness apps), including:
- Motion tracking (step count, standing detection)
- Health metrics (calories, altitude calculations)
- Data persistence (local storage, cache, DB operations)
- Synchronization (cloud sync, auto-backup)
- Lifecycle events (screen on/off, app initialization)

Format:
  <Timestamp>|<Component>|<PID>|<Message>

Example:
  20171223-22:15:29:792|Step_LSC|30002312|onStandStepChanged 3580

The parser extracts structured data into the unified ParsedLogEvent schema.
"""

import re
from datetime import datetime
from typing import Dict, Optional
from app.parsers.base_parser import BaseParser
from app.parsers.log_event_schema import ParsedLogEvent, EventGroup


class HealthAppParser(BaseParser):
    """
    Parses HealthApp (Huawei fitness tracker) logs into unified ParsedLogEvent schema.
    
    Handles motion tracking, health metrics, data persistence, and synchronization events.
    """

    def __init__(self):
        # Event templates (E1-E75 from HealthApp_2k.log_templates.csv)
        pass

    def parse(self, message: str) -> Dict:
        """
        Parse a HealthApp log line into structured ParsedLogEvent.
        
        Format: <Timestamp>|<Component>|<PID>|<Message>
        
        Args:
            message: Raw log line
            
        Returns:
            Dict matching ParsedLogEvent schema
        """
        try:
            # Split by pipe delimiter
            parts = message.split("|")
            
            if len(parts) < 4:
                return self._unknown_event(message)
            
            timestamp_str = parts[0]  # YYYYMMDDHHMMSSmmm format
            component = parts[1]
            pid = parts[2]
            message_content = parts[3]
            
            # Parse timestamp
            timestamp_iso = self._parse_timestamp(timestamp_str)
            
            # Route based on component and message pattern
            return self._route_event(component, pid, timestamp_iso, message_content)
                
        except Exception:
            return self._unknown_event(message)

    def _parse_timestamp(self, ts: str) -> Optional[str]:
        """
        Parse HealthApp timestamp format: YYYYMMDDHHMMSSmmm
        Example: 20171223-22:15:29:606 → 2017-12-23T22:15:29.606
        """
        try:
            # Format: 20171223-22:15:29:606
            # Split by dash: [20171223, 22:15:29:606]
            if "-" not in ts:
                return None
            
            date_part, time_part = ts.split("-")
            # date_part: 20171223
            # time_part: 22:15:29:606
            
            year = date_part[0:4]    # 2017
            month = date_part[4:6]   # 12
            day = date_part[6:8]     # 23
            
            time_parts = time_part.split(":")  # [22, 15, 29, 606]
            if len(time_parts) < 4:
                return None
            
            hour = time_parts[0]
            minute = time_parts[1]
            second = time_parts[2]
            millis = time_parts[3]
            
            # Format as ISO: YYYY-MM-DDTHH:MM:SS.mmm
            iso_timestamp = f"{year}-{month}-{day}T{hour}:{minute}:{second}.{millis}"
            
            return iso_timestamp
        except (ValueError, IndexError):
            return None

    def _route_event(self, component: str, pid: str, timestamp: Optional[str], 
                     message: str) -> Dict:
        """Route log to appropriate handler based on component and message pattern."""
        
        # Step_LSC events: motion tracking
        if component == "Step_LSC":
            return self._parse_step_lsc(pid, timestamp, message)
        
        # Step_StandReportReceiver events: reports
        elif component == "Step_StandReportReceiver":
            return self._parse_report(pid, timestamp, message)
        
        # Step_SPUtils events: persistent storage
        elif component == "Step_SPUtils":
            return self._parse_sputils(pid, timestamp, message)
        
        # Step_ExtSDM events: metrics calculation
        elif component == "Step_ExtSDM":
            return self._parse_extsdm(pid, timestamp, message)
        
        # Step_StandStepCounter events: sensor data
        elif component == "Step_StandStepCounter":
            return self._parse_sensor(pid, timestamp, message)
        
        # Generic component handling (fallback)
        else:
            return self._parse_generic(component, pid, timestamp, message)

    def _parse_step_lsc(self, pid: str, timestamp: Optional[str], message: str) -> Dict:
        """Parse Step_LSC (motion tracking) events."""
        
        # E42: onStandStepChanged <*>
        if message.startswith("onStandStepChanged"):
            match = re.search(r"onStandStepChanged\s+(\d+)", message)
            if match:
                step_count = match.group(1)
                return ParsedLogEvent(
                    event_type="step_count_changed",
                    event_group="motion",
                    component="Step_LSC",
                    template="onStandStepChanged <*>",
                    template_id=42,
                    timestamp=timestamp,
                    status="success",
                    metadata={
                        "pid": pid,
                        "step_count": int(step_count),
                    }
                ).__dict__
        
        # E39: onExtend:<*> <*> <*> <*>
        if message.startswith("onExtend:"):
            match = re.search(r"onExtend:(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", message)
            if match:
                timestamp_val = match.group(1)
                param1 = match.group(2)
                param2 = match.group(3)
                param3 = match.group(4)
                return ParsedLogEvent(
                    event_type="motion_extended",
                    event_group="motion",
                    component="Step_LSC",
                    template="onExtend:<*> <*> <*> <*>",
                    template_id=39,
                    timestamp=timestamp,
                    status="success",
                    metadata={
                        "pid": pid,
                        "event_timestamp": int(timestamp_val),
                        "acceleration_x": int(param1),
                        "acceleration_y": int(param2),
                        "acceleration_z": int(param3),
                    }
                ).__dict__
        
        # E43: processHandleBroadcastAction action:android.intent.action.SCREEN_ON
        if "processHandleBroadcastAction" in message:
            if "SCREEN_ON" in message:
                return ParsedLogEvent(
                    event_type="screen_on_action",
                    event_group="lifecycle",
                    component="Step_LSC",
                    template="processHandleBroadcastAction action:android.intent.action.SCREEN_ON",
                    template_id=43,
                    timestamp=timestamp,
                    status="success",
                    metadata={"pid": pid}
                ).__dict__
        
        # Fallback
        return self._unknown_event(message)

    def _parse_report(self, pid: str, timestamp: Optional[str], message: str) -> Dict:
        """Parse Step_StandReportReceiver events."""
        
        # E41: onReceive action: android.intent.action.SCREEN_ON
        if "onReceive action: android.intent.action.SCREEN_ON" in message:
            return ParsedLogEvent(
                event_type="screen_on_received",
                event_group="lifecycle",
                component="Step_StandReportReceiver",
                template="onReceive action: android.intent.action.SCREEN_ON",
                template_id=41,
                timestamp=timestamp,
                status="success",
                metadata={"pid": pid}
            ).__dict__
        
        # E40: onReceive action: android.intent.action.SCREEN_OFF
        if "onReceive action: android.intent.action.SCREEN_OFF" in message:
            return ParsedLogEvent(
                event_type="screen_off_received",
                event_group="lifecycle",
                component="Step_StandReportReceiver",
                template="onReceive action: android.intent.action.SCREEN_OFF",
                template_id=40,
                timestamp=timestamp,
                status="success",
                metadata={"pid": pid}
            ).__dict__
        
        # E47: REPORT : <*> <*> <*> <*>
        if message.startswith("REPORT :"):
            match = re.search(r"REPORT\s+:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)", message)
            if match:
                steps = match.group(1)
                stands = match.group(2)
                calories = match.group(3)
                altitude = match.group(4)
                return ParsedLogEvent(
                    event_type="health_metrics_report",
                    event_group="report",
                    component="Step_StandReportReceiver",
                    template="REPORT : <*> <*> <*> <*>",
                    template_id=47,
                    timestamp=timestamp,
                    status="success",
                    metadata={
                        "pid": pid,
                        "steps": int(steps),
                        "stands": int(stands),
                        "calories": int(calories),
                        "altitude": int(altitude),
                    }
                ).__dict__
        
        # Fallback
        return self._unknown_event(message)

    def _parse_sputils(self, pid: str, timestamp: Optional[str], message: str) -> Dict:
        """Parse Step_SPUtils (storage utility) events."""
        
        # E22: getTodayTotalDetailSteps = <*>##<*>##<*>##<*>##<*>##<*>
        if "getTodayTotalDetailSteps =" in message:
            match = re.search(r"getTodayTotalDetailSteps\s+=\s+(.+)", message)
            if match:
                data_str = match.group(1)
                parts = data_str.split("##")
                if len(parts) >= 6:
                    return ParsedLogEvent(
                        event_type="step_data_retrieved",
                        event_group="persistence",
                        component="Step_SPUtils",
                        template="getTodayTotalDetailSteps = <*>##<*>##<*>##<*>##<*>##<*>",
                        template_id=22,
                        timestamp=timestamp,
                        status="success",
                        metadata={
                            "pid": pid,
                            "start_time": int(parts[0]) if parts[0].isdigit() else parts[0],
                            "field1": int(parts[1]) if parts[1].isdigit() else parts[1],
                            "field2": int(parts[2]) if parts[2].isdigit() else parts[2],
                            "field3": int(parts[3]) if parts[3].isdigit() else parts[3],
                            "field4": int(parts[4]) if parts[4].isdigit() else parts[4],
                            "field5": int(parts[5]) if parts[5].isdigit() else parts[5],
                            "raw_data": data_str,
                        }
                    ).__dict__
        
        # E58: setTodayTotalDetailSteps=<*>
        if "setTodayTotalDetailSteps=" in message:
            match = re.search(r"setTodayTotalDetailSteps=(.+)", message)
            if match:
                data_str = match.group(1)
                parts = data_str.split("##")
                if len(parts) >= 6:
                    return ParsedLogEvent(
                        event_type="step_data_updated",
                        event_group="persistence",
                        component="Step_SPUtils",
                        template="setTodayTotalDetailSteps=<*>",
                        template_id=58,
                        timestamp=timestamp,
                        status="success",
                        metadata={
                            "pid": pid,
                            "start_time": int(parts[0]) if parts[0].isdigit() else parts[0],
                            "field1": int(parts[1]) if parts[1].isdigit() else parts[1],
                            "field2": int(parts[2]) if parts[2].isdigit() else parts[2],
                            "field3": int(parts[3]) if parts[3].isdigit() else parts[3],
                            "field4": int(parts[4]) if parts[4].isdigit() else parts[4],
                            "field5": int(parts[5]) if parts[5].isdigit() else parts[5],
                            "raw_data": data_str,
                        }
                    ).__dict__
        
        # Fallback
        return self._unknown_event(message)

    def _parse_extsdm(self, pid: str, timestamp: Optional[str], message: str) -> Dict:
        """Parse Step_ExtSDM (metrics calculation) events."""
        
        # E4: calculateCaloriesWithCache totalCalories=<*>
        if "calculateCaloriesWithCache" in message:
            match = re.search(r"totalCalories=(\d+)", message)
            if match:
                calories = match.group(1)
                return ParsedLogEvent(
                    event_type="calories_calculated",
                    event_group="report",
                    component="Step_ExtSDM",
                    template="calculateCaloriesWithCache totalCalories=<*>",
                    template_id=4,
                    timestamp=timestamp,
                    status="success",
                    metadata={
                        "pid": pid,
                        "total_calories": int(calories),
                    }
                ).__dict__
        
        # E3: calculateAltitudeWithCache totalAltitude=<*>
        if "calculateAltitudeWithCache" in message:
            match = re.search(r"totalAltitude=(\d+)", message)
            if match:
                altitude = match.group(1)
                return ParsedLogEvent(
                    event_type="altitude_calculated",
                    event_group="report",
                    component="Step_ExtSDM",
                    template="calculateAltitudeWithCache totalAltitude=<*>",
                    template_id=3,
                    timestamp=timestamp,
                    status="success",
                    metadata={
                        "pid": pid,
                        "total_altitude": int(altitude),
                    }
                ).__dict__
        
        # Fallback
        return self._unknown_event(message)

    def _parse_sensor(self, pid: str, timestamp: Optional[str], message: str) -> Dict:
        """Parse Step_StandStepCounter (sensor) events."""
        
        # E12: flush sensor data
        if message.strip() == "flush sensor data":
            return ParsedLogEvent(
                event_type="sensor_data_flushed",
                event_group="persistence",
                component="Step_StandStepCounter",
                template="flush sensor data",
                template_id=12,
                timestamp=timestamp,
                status="success",
                metadata={"pid": pid}
            ).__dict__
        
        # Fallback
        return self._unknown_event(message)

    def _parse_generic(self, component: str, pid: str, timestamp: Optional[str], 
                       message: str) -> Dict:
        """Parse generic component events."""
        
        # Try to match common patterns
        
        # Success/result patterns
        if "success" in message.lower():
            event_type = f"{component.lower()}_success"
            return ParsedLogEvent(
                event_type=event_type,
                event_group="system",
                component=component,
                template=message,
                template_id=None,
                timestamp=timestamp,
                status="success",
                metadata={"pid": pid}
            ).__dict__
        
        # Error patterns
        if "error" in message.lower() or "fail" in message.lower():
            event_type = f"{component.lower()}_error"
            return ParsedLogEvent(
                event_type=event_type,
                event_group="error",
                component=component,
                template=message,
                template_id=None,
                timestamp=timestamp,
                status="error",
                metadata={"pid": pid}
            ).__dict__
        
        # Default fallback
        return self._unknown_event(message)

    def _unknown_event(self, message: str) -> Dict:
        """Handle unknown or unparseable log lines."""
        return ParsedLogEvent(
            event_type="unknown",
            event_group="system",
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
