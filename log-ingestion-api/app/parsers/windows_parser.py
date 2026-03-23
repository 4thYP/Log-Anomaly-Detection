"""
Production-grade Windows event log parser for Loghub Windows logs.
Handles CBS/CSI component logs with transaction, package, and service events.
"""

import re
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

from app.parsers.base_parser import BaseParser


@dataclass
class ParsedWindowsLogEvent:
    """Unified schema for all Windows log events"""
    event_type: str
    component: str
    template_id: Optional[str] = None
    template: str = ""
    level: str = "Info"
    hresult: Optional[str] = None
    error_name: Optional[str] = None
    status: Optional[str] = None
    session_id: Optional[str] = None
    package_name: Optional[str] = None
    client: Optional[str] = None
    file_path: Optional[str] = None
    sequence_number: Optional[int] = None
    handle: Optional[str] = None
    transaction_id: Optional[int] = None
    version: Optional[str] = None
    raw_message: str = ""
    parsed_successfully: bool = True
    confidence: float = 1.0
    message_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class WindowsParser(BaseParser):
    """
    Parser for Windows CBS/CSI event log entries from Loghub dataset.
    
    Handles:
    - Service lifecycle (TrustedInstaller start/stop)
    - Transaction management (NT transactions, CSI operations)
    - Package operations (applicability, installation)
    - Error events (manifest, parse, upload failures)
    - System operations (registry, scavenge, cache)
    - Telemetry (SQM errors)
    """

    # ============================================================================
    # REGEX PATTERNS - Production-grade with named groups
    # ============================================================================

    # Header pattern: "YYYY-MM-DD HH:MM:SS, Level Component Message"
    # Note: Level and Component are padded/fixed-width
    HEADER_PATTERN = re.compile(
        r"^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}),\s+(\w+)\s+(\w+)\s+(.*)$"
    )

    # Error code patterns
    HRESULT_PATTERN = re.compile(r"HRESULT\s*=\s*(0x[0-9a-fA-F]+)\s*-\s*(\S+)")
    ERROR_CODE_PATTERN = re.compile(r"\[HRESULT\s*=\s*(0x[0-9a-fA-F]+)\s*-\s*(\w+)\]")

    # Transaction patterns
    TRANSACTION_CREATE = re.compile(
        r"Created\s+NT\s+transaction\s+\(seq\s+(\d+)\)\s+result\s+(0x[0-9a-fA-F]+),\s+handle\s+(@0x[0-9a-fA-F]+)"
    )
    TRANSACTION_INITIALIZE = re.compile(
        r"CSI\s+Transaction\s+@(0x[0-9a-fA-F]+)\s+initialized"
    )
    TRANSACTION_RESOLVED = re.compile(
        r"CSI\s+Transaction\s+@(0x[0-9a-fA-F]+)\s+destroyed"
    )

    # Session patterns
    SESSION_INITIALIZED = re.compile(
        r"Session:\s+(\d+)_(\d+)\s+initialized\s+by\s+client\s+(\S+)"
    )
    SESSION_DESTROYED = re.compile(
        r"Session:\s+(\d+)_(\d+).*destroyed"
    )

    # Package patterns
    PACKAGE_APPLICABILITY = re.compile(
        r"Read\s+out\s+cached\s+package\s+applicability\s+for\s+package:\s+([^,]+),\s+ApplicableState:\s+(\d+),\s+CurrentState:(\d+)"
    )
    PACKAGE_ERROR = re.compile(
        r"Failed\s+to\s+internally\s+open\s+package\.\s+\[HRESULT\s*=\s*(0x[0-9a-fA-F]+)\s*-\s*(\S+)\]"
    )

    # Service patterns
    SERVICE_START = re.compile(
        r"TrustedInstaller\s+service\s+starts\s+successfully"
    )
    SERVICE_SHUTDOWN = re.compile(
        r"Ending\s+the\s+TrustedInstaller\s+main\s+loop"
    )
    SERVICE_INIT_START = re.compile(
        r"Starting\s+TrustedInstaller\s+initialization"
    )
    SERVICE_INIT_END = re.compile(
        r"Ending\s+TrustedInstaller\s+initialization"
    )

    # SQM/Telemetry patterns
    SQM_UPLOAD_FAILED = re.compile(
        r"SQM:\s+Failed\s+to\s+start\s+upload\s+with\s+file\s+pattern:\s+([^,]+),\s+flags:\s+(0x\S+)\s+\[HRESULT\s*=\s*(0x[0-9a-fA-F]+)\s*-\s*(\S+)\]"
    )
    SQM_UPLOAD_FAILED_ALT = re.compile(
        r"SQM:\s+Failed\s+to\s+start\s+\w+\s+\w+\s+upload.\s+\[HRESULT\s*=\s*(0x[0-9a-fA-F]+)\s*-\s*(\S+)\]"
    )

    # Error indicator patterns
    WARNING_UNRECOGNIZED = re.compile(
        r"Warning:\s+Unrecognized\s+(\w+)\s+attribute"
    )
    EXPECTING_ATTRIBUTE = re.compile(
        r"Expecting\s+attribute\s+name\s+\[HRESULT\s*=\s*(0x[0-9a-fA-F]+)\s*-\s*(\S+)\]"
    )
    FAILED_GET_ELEMENT = re.compile(
        r"Failed\s+to\s+get\s+next\s+element\s+\[HRESULT\s*=\s*(0x[0-9a-fA-F]+)\s*-\s*(\S+)\]"
    )

    # Registry patterns
    LOAD_REGISTRY = re.compile(
        r"Loading\s+offline\s+registry\s+hive:\s+([^,]+),\s+into\s+registry\s+key\s+'([^']+)'"
    )
    UNLOAD_REGISTRY = re.compile(
        r"Unloading\s+offline\s+registry\s+hive:\s+(\S+)"
    )

    # Scavenge patterns
    SCAVENGE_BEGIN = re.compile(r"Scavenge:\s+Begin\s+CSI\s+Store")
    SCAVENGE_COMPLETE = re.compile(r"Scavenge:\s+Completed,\s+disposition:\s+(\d+)")

    # ============================================================================
    # PARSER IMPLEMENTATION
    # ============================================================================

    def parse(self, log_line: str) -> Dict[str, Any]:
        """
        Parse a single Windows event log line.

        Args:
            log_line: Raw event log line

        Returns:
            Dictionary with parsed event in standardized format
        """
        try:
            # Parse header
            header_match = self.HEADER_PATTERN.match(log_line)
            if not header_match:
                return self._unknown_log(log_line)

            date_str, time_str, level, component, message = header_match.groups()

            # Route to appropriate parser
            if component == "CBS":
                return self._parse_cbs(message, level, log_line)
            elif component == "CSI":
                return self._parse_csi(message, level, log_line)
            else:
                return self._parse_generic(component, message, level, log_line)

        except Exception as e:
            return self._unknown_log(log_line, str(e))

    # ============================================================================
    # COMPONENT PARSERS
    # ============================================================================

    def _parse_cbs(self, message: str, level: str, log_line: str) -> Dict[str, Any]:
        """Parse CBS (Component-Based Servicing) events"""

        # Service startup
        if self.SERVICE_START.search(message):
            return self._build_event(
                event_type="service_start",
                component="CBS",
                template_id="E48",
                template="TrustedInstaller service starts successfully.",
                level=level,
                status="success",
                raw_message=message
            )

        # Service shutdown
        elif self.SERVICE_SHUTDOWN.search(message):
            return self._build_event(
                event_type="service_stop",
                component="CBS",
                template_id="E15",
                template="Ending the TrustedInstaller main loop.",
                level=level,
                status="success",
                raw_message=message
            )

        # Service init start
        elif self.SERVICE_INIT_START.search(message):
            return self._build_event(
                event_type="service_init",
                component="CBS",
                template_id="E46",
                template="Starting TrustedInstaller initialization.",
                level=level,
                status="success",
                raw_message=message
            )

        # Service init end
        elif self.SERVICE_INIT_END.search(message):
            return self._build_event(
                event_type="service_init",
                component="CBS",
                template_id="E17",
                template="Ending TrustedInstaller initialization.",
                level=level,
                status="success",
                raw_message=message
            )

        # Package applicability
        elif "Read out cached package applicability" in message:
            match = self.PACKAGE_APPLICABILITY.search(message)
            if match:
                pkg_name, app_state, curr_state = match.groups()
                return self._build_event(
                    event_type="package_applicability",
                    component="CBS",
                    template_id="E29",
                    template="Read out cached package applicability for package: <*>, ApplicableState: <*>, CurrentState:<*>",
                    level=level,
                    status="success",
                    package_name=pkg_name,
                    raw_message=message
                )

        # Package error - Failed to internally open
        elif self.PACKAGE_ERROR.search(message):
            match = self.PACKAGE_ERROR.search(message)
            if match:
                hresult, error_name = match.groups()
                return self._build_event(
                    event_type="package_error",
                    component="CBS",
                    template_id="E21",
                    template="Failed to internally open package. [HRESULT = <*> - CBS_E_INVALID_PACKAGE]",
                    level=level,
                    status="failure",
                    hresult=hresult,
                    error_name=error_name,
                    raw_message=message
                )

        # SQM upload error
        elif self.SQM_UPLOAD_FAILED.search(message):
            match = self.SQM_UPLOAD_FAILED.search(message)
            if match:
                file_path, flags, hresult, error_name = match.groups()
                return self._build_event(
                    event_type="upload_error",
                    component="CBS",
                    template_id="E39",
                    template="SQM: Failed to start upload with file pattern: <*>, flags: <*> [HRESULT = <*> - E_FAIL]",
                    level=level,
                    status="failure",
                    hresult=hresult,
                    error_name=error_name,
                    file_path=file_path,
                    raw_message=message
                )
        elif self.SQM_UPLOAD_FAILED_ALT.search(message):
            match = self.SQM_UPLOAD_FAILED_ALT.search(message)
            if match:
                hresult, error_name = match.groups()
                return self._build_event(
                    event_type="upload_error",
                    component="CBS",
                    template_id="E38",
                    template="SQM: Failed to start standard sample upload. [HRESULT = <*> - E_FAIL]",
                    level=level,
                    status="failure",
                    hresult=hresult,
                    error_name=error_name,
                    raw_message=message
                )

        # Session initialization
        elif self.SESSION_INITIALIZED.search(message):
            match = self.SESSION_INITIALIZED.search(message)
            if match:
                id1, id2, client = match.groups()
                session_id = f"{id1}_{id2}"
                return self._build_event(
                    event_type="session_initialized",
                    component="CBS",
                    template_id="E36",
                    template="Session: <*>_<*> initialized by client WindowsUpdateAgent.",
                    level=level,
                    status="success",
                    session_id=session_id,
                    client=client,
                    raw_message=message
                )

        # Error cascade: Expecting attribute name
        elif self.EXPECTING_ATTRIBUTE.search(message):
            match = self.EXPECTING_ATTRIBUTE.search(message)
            if match:
                hresult, error_name = match.groups()
                return self._build_event(
                    event_type="manifest_error",
                    component="CBS",
                    template_id="E18",
                    template="Expecting attribute name [HRESULT = <*> - CBS_E_MANIFEST_INVALID_ITEM]",
                    level=level,
                    status="failure",
                    hresult=hresult,
                    error_name=error_name,
                    raw_message=message
                )

        # Error cascade: Failed to get next element
        elif self.FAILED_GET_ELEMENT.search(message):
            match = self.FAILED_GET_ELEMENT.search(message)
            if match:
                hresult, error_name = match.groups()
                return self._build_event(
                    event_type="parse_error",
                    component="CBS",
                    template_id="E20",
                    template="Failed to get next element [HRESULT = <*> - CBS_E_MANIFEST_INVALID_ITEM]",
                    level=level,
                    status="failure",
                    hresult=hresult,
                    error_name=error_name,
                    raw_message=message
                )

        # Warning: Unrecognized attribute
        elif self.WARNING_UNRECOGNIZED.search(message):
            match = self.WARNING_UNRECOGNIZED.search(message)
            attr_type = match.group(1) if match else "unknown"
            return self._build_event(
                event_type="parse_error",
                component="CBS",
                template_id="E50",
                template="Warning: Unrecognized packageExtended attribute.",
                level=level,
                status="warning",
                raw_message=message
            )

        # Generic CBS event
        return self._build_event(
            event_type="system_info",
            component="CBS",
            level=level,
            status="info",
            raw_message=message,
            parsed_successfully=False,
            confidence=0.5
        )

    def _parse_csi(self, message: str, level: str, log_line: str) -> Dict[str, Any]:
        """Parse CSI (Component Servicing Infrastructure) events"""

        # Transaction created
        if self.TRANSACTION_CREATE.search(message):
            match = self.TRANSACTION_CREATE.search(message)
            if match:
                seq, result, handle = match.groups()
                status = "success" if result == "0x00000000" else "failure"
                return self._build_event(
                    event_type="transaction_create",
                    component="CSI",
                    template_id="E1",
                    template="<*> Created NT transaction (seq <*>) result <*>, handle @<*>",
                    level=level,
                    status=status,
                    hresult=result,
                    sequence_number=int(seq),
                    handle=handle,
                    raw_message=message
                )

        # CSI perf trace
        elif "CSI perf trace:" in message:
            return self._build_event(
                event_type="system_info",
                component="CSI",
                template_id="E3",
                template="<*> CSI perf trace:",
                level=level,
                status="info",
                raw_message=message
            )

        # Store initialized
        elif "CSI Store" in message and "initialized" in message:
            match = re.search(r"CSI Store (\d+) \((0x[0-9a-fA-F]+)\) initialized", message)
            if match:
                store_id, addr = match.groups()
                return self._build_event(
                    event_type="cache_operation",
                    component="CSI",
                    template_id="E4",
                    template="<*> CSI Store <*> (<*>) initialized",
                    level=level,
                    status="success",
                    raw_message=message
                )

        # WcpInitialize
        elif "WcpInitialize" in message:
            return self._build_event(
                event_type="system_info",
                component="CSI",
                template_id="E13",
                template="<*>@<*>/<*>/<*>:<*>:<*>:<*>.<*> WcpInitialize (wcp.dll version <*>) called (stack @<*>)",
                level=level,
                status="info",
                raw_message=message
            )

        # Generic CSI event
        return self._build_event(
            event_type="system_info",
            component="CSI",
            level=level,
            status="info",
            raw_message=message,
            parsed_successfully=False,
            confidence=0.5
        )

    def _parse_generic(
        self, component: str, message: str, level: str, log_line: str
    ) -> Dict[str, Any]:
        """Generic fallback parser for unknown components"""
        return self._build_event(
            event_type="system_info",
            component=component,
            level=level,
            status="info",
            raw_message=message,
            parsed_successfully=False,
            confidence=0.3
        )

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def _build_event(
        self,
        event_type: str,
        component: str,
        template_id: Optional[str] = None,
        template: str = "",
        level: str = "Info",
        hresult: Optional[str] = None,
        error_name: Optional[str] = None,
        status: Optional[str] = None,
        session_id: Optional[str] = None,
        package_name: Optional[str] = None,
        client: Optional[str] = None,
        file_path: Optional[str] = None,
        sequence_number: Optional[int] = None,
        handle: Optional[str] = None,
        transaction_id: Optional[int] = None,
        version: Optional[str] = None,
        raw_message: str = "",
        parsed_successfully: bool = True,
        confidence: float = 1.0,
    ) -> Dict[str, Any]:
        """Build a standardized event dictionary"""
        event = ParsedWindowsLogEvent(
            event_type=event_type,
            component=component,
            template_id=template_id,
            template=template,
            level=level,
            hresult=hresult,
            error_name=error_name,
            status=status,
            session_id=session_id,
            package_name=package_name,
            client=client,
            file_path=file_path,
            sequence_number=sequence_number,
            handle=handle,
            transaction_id=transaction_id,
            version=version,
            raw_message=raw_message,
            parsed_successfully=parsed_successfully,
            confidence=confidence,
        )
        return event.to_dict()

    def _unknown_log(self, log_line: str, error: str = "") -> Dict[str, Any]:
        """Handle unparseable logs"""
        return ParsedWindowsLogEvent(
            event_type="unknown",
            component="unknown",
            level="Unknown",
            status="parse_error",
            raw_message=log_line[:200],
            parsed_successfully=False,
            confidence=0.0,
            error_name=error if error else "Could not match header pattern"
        ).to_dict()
