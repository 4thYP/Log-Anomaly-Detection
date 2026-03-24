"""
Production-grade Windows event log parser for Loghub Windows logs.

Handles CBS/CSI component logs with transaction, package, service, and SQM events.
Conforms to the unified ParsedLogEvent schema for consistent feature extraction.

Components:
- CBS (Component-Based Servicing): Service lifecycle, package ops, SQM telemetry
- CSI (Component Servicing Infrastructure): Transaction management, store operations
"""

import re
from typing import Dict, Optional, Any
from datetime import datetime
from app.parsers.base_parser import BaseParser
from app.parsers.log_event_schema import (
    ParsedLogEvent,
    EventGroup,
    WindowsEventType,
    template_id_from_csv,
)


class WindowsParser(BaseParser):
    """
    Parser for Windows CBS/CSI event log entries from Loghub dataset.
    
    Implements:
    - Service lifecycle (TrustedInstaller start/stop/init)
    - Transaction management (NT transactions, CSI operations)
    - Package operations (applicability, installation, errors)
    - Error events (manifest, parse, upload failures)
    - System operations (registry, scavenge, cache)
    - Telemetry (SQM errors)
    
    All returned events conform to ParsedLogEvent unified schema.
    """

    # ============================================================================
    # TEMPLATE ID MAPPING from Windows_2k.log_templates.csv
    # ============================================================================
    
    TEMPLATES = {
        "E1": "Created NT transaction (seq <*>) result <*>, handle @<*>",
        "E2": "Creating NT transaction (seq <*>), objectname [<*>]\"(null)\"",
        "E3": "<*> CSI perf trace:",
        "E4": "<*> CSI Store <*> (<*>) initialized",
        "E5": "<*> IAdvancedInstallerAwareStore_ResolvePendingTransactions (call <*>) (flags = <*>, progress = <*>, phase = <*>, pdwDisposition = @<*>",
        "E6": "<*> ICSITransaction::Commit calling IStorePendingTransaction::Apply - coldpatching=FALSE applyflags=<*>",
        "E7": "<*> Performing <*> operations; <*> are not lock/unlock and follow:",
        "E8": "<*> Store coherency cookie matches last scavenge cookie, skipping scavenge.",
        "E9": "<*>@<*>/<*>/<*>:<*>:<*>:<*>.<*> CSI Transaction @<*> destroyed",
        "E10": "<*>@<*>/<*>/<*>:<*>:<*>:<*>.<*> CSI Transaction @<*> initialized for deployment engine {<*>} with flags <*> and client id [<*>]\"<*>/\"",
        "E11": "<*>@<*>/<*>/<*>:<*>:<*>:<*>.<*> PopulateComponentFamiliesKey - Begin",
        "E12": "<*>@<*>/<*>/<*>:<*>:<*>:<*>.<*> PopulateComponentFamiliesKey - End",
        "E13": "<*>@<*>/<*>/<*>:<*>:<*>:<*>.<*> WcpInitialize (wcp.dll version <*>) called (stack @<*>)",
        "E14": "Disabling manifest caching, because the image is not writeable.",
        "E15": "Ending the TrustedInstaller main loop.",
        "E16": "Ending TrustedInstaller finalization.",
        "E17": "Ending TrustedInstaller initialization.",
        "E18": "Expecting attribute name [HRESULT = <*> - CBS_E_MANIFEST_INVALID_ITEM]",
        "E19": "Failed to create backup log cab. [HRESULT = <*> - ERROR_INVALID_FUNCTION]",
        "E20": "Failed to get next element [HRESULT = <*> - CBS_E_MANIFEST_INVALID_ITEM]",
        "E21": "Failed to internally open package. [HRESULT = <*> - CBS_E_INVALID_PACKAGE]",
        "E22": "Idle processing thread terminated normally",
        "E23": "Loaded Servicing Stack <*> with Core: <*>\\cbscore.dll",
        "E24": "Loading offline registry hive: <*>, into registry key '<*>' from path '<*>'.",
        "E25": "No startup processing required, TrustedInstaller service was not set as autostart, or else a reboot is still pending.",
        "E26": "NonStart: Checking to ensure startup processing was not required.",
        "E27": "NonStart: Success, startup processing not required as expected.",
        "E28": "Offline image is: read-only",
        "E29": "Read out cached package applicability for package: <*>, ApplicableState: <*>, CurrentState:<*>",
        "E30": "Reboot mark refs incremented to: <*>",
        "E31": "Reboot mark refs: <*>",
        "E32": "Scavenge: Begin CSI Store",
        "E33": "Scavenge: Completed, disposition: <*>",
        "E34": "Scavenge: Starts",
        "E35": "Session: <*>_<*> initialized by client SPP.",
        "E36": "Session: <*>_<*> initialized by client WindowsUpdateAgent.",
        "E37": "SQM: Cleaning up report files older than <*> days.",
        "E38": "SQM: Failed to start standard sample upload. [HRESULT = <*> - E_FAIL]",
        "E39": "SQM: Failed to start upload with file pattern: <*>, flags: <*> [HRESULT = <*> - E_FAIL]",
        "E40": "SQM: Initializing online with Windows opt-in: False",
        "E41": "SQM: Queued <*> file(s) for upload with pattern: <*>, flags: <*>",
        "E42": "SQM: Requesting upload of all unsent reports.",
        "E43": "SQM: Warning: Failed to upload all unsent reports. [HRESULT = <*> - E_FAIL]",
        "E44": "Starting the TrustedInstaller main loop.",
        "E45": "Starting TrustedInstaller finalization.",
        "E46": "Starting TrustedInstaller initialization.",
        "E47": "Startup processing thread terminated normally",
        "E48": "TrustedInstaller service starts successfully.",
        "E49": "Unloading offline registry hive: <*>",
        "E50": "Warning: Unrecognized packageExtended attribute.",
    }

    # ============================================================================
    # REGEX PATTERNS - Production-grade with named groups
    # ============================================================================

    # Header pattern: "YYYY-MM-DD HH:MM:SS, Level Component Message"
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
    TRANSACTION_DESTROY = re.compile(
        r"CSI\s+Transaction\s+@(0x[0-9a-fA-F]+)\s+destroyed"
    )

    # Session patterns
    SESSION_INITIALIZED = re.compile(
        r"Session:\s+(\d+)_(\d+)\s+initialized\s+by\s+client\s+(\w+)"
    )
    SESSION_DESTROYED = re.compile(
        r"Session:\s+(\d+)_(\d+).*destroyed"
    )

    # Package patterns
    PACKAGE_APPLICABILITY = re.compile(
        r"Read\s+out\s+cached\s+package\s+applicability\s+for\s+package:\s+([^,]+),\s+ApplicableState:\s+(\d+),\s+CurrentState:(\d+)"
    )
    PACKAGE_ERROR = re.compile(
        r"Failed\s+to\s+(internally\s+)?open\s+package\.\s+\[HRESULT\s*=\s*(0x[0-9a-fA-F]+)\s*-\s*(\S+)\]"
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

    # System/Store patterns
    LOAD_SERVICING_STACK = re.compile(
        r"Loaded\s+Servicing\s+Stack\s+(.+?)\s+with\s+Core:\s+(.+)"
    )
    CSI_STORE_INITIALIZED = re.compile(
        r"CSI\s+Store\s+(\d+)\s+\((0x[0-9a-fA-F]+)\)\s+initialized"
    )
    WCP_INITIALIZE = re.compile(
        r"WcpInitialize\s+\(wcp\.dll\s+version\s+(.+?)\)\s+called"
    )
    SCAVENGE_BEGIN = re.compile(r"Scavenge:\s+Begin\s+CSI\s+Store")
    SCAVENGE_COMPLETE = re.compile(r"Scavenge:\s+Completed,\s+disposition:\s+(\d+)")
    SCAVENGE_START = re.compile(r"Scavenge:\s+Starts")

    # Registry patterns
    LOAD_REGISTRY = re.compile(
        r"Loading\s+offline\s+registry\s+hive:\s+([^,]+),\s+into\s+registry\s+key\s+'([^']+)'"
    )
    UNLOAD_REGISTRY = re.compile(
        r"Unloading\s+offline\s+registry\s+hive:\s+(\S+)"
    )

    # SQM/Telemetry patterns
    SQM_UPLOAD_FAILED_PATTERN = re.compile(
        r"SQM:\s+Failed\s+to\s+start\s+upload\s+with\s+file\s+pattern:\s+([^,]+),\s+flags:\s+(0x\S+)\s+\[HRESULT\s*=\s*(0x[0-9a-fA-F]+)\s*-\s*(\S+)\]"
    )
    SQM_UPLOAD_FAILED_ALT = re.compile(
        r"SQM:\s+Failed\s+to\s+start\s+\w+\s+\w+\s+upload\.\s+\[HRESULT\s*=\s*(0x[0-9a-fA-F]+)\s*-\s*(\S+)\]"
    )

    # Error indicator patterns
    EXPECTING_ATTRIBUTE = re.compile(
        r"Expecting\s+attribute\s+name\s+\[HRESULT\s*=\s*(0x[0-9a-fA-F]+)\s*-\s*(\S+)\]"
    )
    FAILED_GET_ELEMENT = re.compile(
        r"Failed\s+to\s+get\s+next\s+element\s+\[HRESULT\s*=\s*(0x[0-9a-fA-F]+)\s*-\s*(\S+)\]"
    )
    WARNING_UNRECOGNIZED = re.compile(
        r"Warning:\s+Unrecognized\s+(\w+)\s+attribute"
    )

    # ============================================================================
    # PARSER IMPLEMENTATION
    # ============================================================================

    def parse(self, log_line: str) -> Dict[str, Any]:
        """
        Parse a single Windows event log line into ParsedLogEvent format.

        Args:
            log_line: Raw event log line

        Returns:
            Dictionary representation of ParsedLogEvent (via .to_dict())
            
        Raises:
            Implicitly handles all exceptions and returns unknown_event
        """
        try:
            # Parse header to extract timestamp and metadata
            header_match = self.HEADER_PATTERN.match(log_line)
            if not header_match:
                return ParsedLogEvent.unknown_event(
                    log_line=log_line[:100],
                    component="unknown",
                    error="Could not match header pattern"
                ).to_dict()

            date_str, time_str, level, component, message = header_match.groups()
            timestamp = self._parse_timestamp(date_str, time_str)

            # Route to appropriate parser by component
            if component == "CBS":
                return self._parse_cbs(message, level, timestamp, log_line).to_dict()
            elif component == "CSI":
                return self._parse_csi(message, level, timestamp, log_line).to_dict()
            else:
                return ParsedLogEvent.unknown_event(
                    log_line=log_line[:100],
                    component=component,
                    timestamp=timestamp
                ).to_dict()

        except Exception as e:
            return ParsedLogEvent.unknown_event(
                log_line=log_line[:100],
                component="unknown",
                error=str(e)
            ).to_dict()

    # ============================================================================
    # TIMESTAMP CONVERSION
    # ============================================================================

    @staticmethod
    def _parse_timestamp(date_str: str, time_str: str) -> str:
        """
        Parse timestamp from log header and convert to ISO 8601 format.
        
        Args:
            date_str: Date in "YYYY-MM-DD" format
            time_str: Time in "HH:MM:SS" format
            
        Returns:
            ISO 8601 timestamp string (YYYY-MM-DDTHH:MM:SS)
        """
        try:
            dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
            return dt.isoformat()
        except (ValueError, TypeError):
            return ""

    # ============================================================================
    # CBS (COMPONENT-BASED SERVICING) PARSER
    # ============================================================================

    def _parse_cbs(
        self, message: str, level: str, timestamp: str, log_line: str
    ) -> ParsedLogEvent:
        """
        Parse CBS (Component-Based Servicing) events.
        
        Handles:
        - Service lifecycle (start, stop, init)
        - Package operations (applicability, errors)
        - Session management
        - SQM/Telemetry
        - System operations (registry, scavenge)
        """

        # ======================================================================
        # SERVICE LIFECYCLE EVENTS
        # ======================================================================

        # TrustedInstaller service starts successfully
        if self.SERVICE_START.search(message):
            return ParsedLogEvent(
                event_type=WindowsEventType.SERVICE_START.value,
                event_group=EventGroup.SERVICE.value,
                component="CBS",
                template=self.TEMPLATES["E48"],
                template_id=template_id_from_csv("E48"),
                timestamp=timestamp,
                status="success",
                metadata={},
                parsed_successfully=True,
                confidence=1.0,
            )

        # Ending the TrustedInstaller main loop
        if self.SERVICE_SHUTDOWN.search(message):
            return ParsedLogEvent(
                event_type=WindowsEventType.SERVICE_STOP.value,
                event_group=EventGroup.SERVICE.value,
                component="CBS",
                template=self.TEMPLATES["E15"],
                template_id=template_id_from_csv("E15"),
                timestamp=timestamp,
                status="success",
                metadata={},
                parsed_successfully=True,
                confidence=1.0,
            )

        # Starting TrustedInstaller initialization
        if self.SERVICE_INIT_START.search(message):
            return ParsedLogEvent(
                event_type=WindowsEventType.SERVICE_INIT_START.value,
                event_group=EventGroup.SERVICE.value,
                component="CBS",
                template=self.TEMPLATES["E46"],
                template_id=template_id_from_csv("E46"),
                timestamp=timestamp,
                status="success",
                metadata={},
                parsed_successfully=True,
                confidence=1.0,
            )

        # Ending TrustedInstaller initialization
        if self.SERVICE_INIT_END.search(message):
            return ParsedLogEvent(
                event_type=WindowsEventType.SERVICE_INIT_END.value,
                event_group=EventGroup.SERVICE.value,
                component="CBS",
                template=self.TEMPLATES["E17"],
                template_id=template_id_from_csv("E17"),
                timestamp=timestamp,
                status="success",
                metadata={},
                parsed_successfully=True,
                confidence=1.0,
            )

        # ======================================================================
        # PACKAGE OPERATIONS
        # ======================================================================

        # Read out cached package applicability
        if self.PACKAGE_APPLICABILITY.search(message):
            match = self.PACKAGE_APPLICABILITY.search(message)
            if match:
                pkg_name, app_state, curr_state = match.groups()
                return ParsedLogEvent(
                    event_type=WindowsEventType.PACKAGE_APPLICABILITY.value,
                    event_group=EventGroup.PACKAGE.value,
                    component="CBS",
                    template=self.TEMPLATES["E29"],
                    template_id=template_id_from_csv("E29"),
                    timestamp=timestamp,
                    status="success",
                    metadata={
                        "package_name": pkg_name.strip(),
                        "applicable_state": int(app_state),
                        "current_state": int(curr_state),
                    },
                    parsed_successfully=True,
                    confidence=1.0,
                )

        # Failed to internally open package
        if self.PACKAGE_ERROR.search(message):
            match = self.PACKAGE_ERROR.search(message)
            if match:
                _, hresult, error_name = match.groups()
                return ParsedLogEvent(
                    event_type=WindowsEventType.PACKAGE_ERROR.value,
                    event_group=EventGroup.PACKAGE.value,
                    component="CBS",
                    template=self.TEMPLATES["E21"],
                    template_id=template_id_from_csv("E21"),
                    timestamp=timestamp,
                    status="failure",
                    metadata={
                        "hresult": hresult,
                        "error_code": error_name,
                    },
                    parsed_successfully=True,
                    confidence=1.0,
                )

        # ======================================================================
        # SESSION MANAGEMENT
        # ======================================================================

        # Session: <id1>_<id2> initialized by client <name>
        if self.SESSION_INITIALIZED.search(message):
            match = self.SESSION_INITIALIZED.search(message)
            if match:
                id1, id2, client = match.groups()
                session_id = f"{id1}_{id2}"
                # Determine template based on client
                if "SPP" in client.upper():
                    template_id = "E35"
                else:
                    template_id = "E36"
                
                return ParsedLogEvent(
                    event_type=WindowsEventType.SESSION_INIT.value,
                    event_group=EventGroup.SESSION.value,
                    component="CBS",
                    template=self.TEMPLATES[template_id],
                    template_id=template_id_from_csv(template_id),
                    timestamp=timestamp,
                    status="success",
                    metadata={
                        "session_id": session_id,
                        "client": client,
                    },
                    parsed_successfully=True,
                    confidence=1.0,
                )

        # ======================================================================
        # SQM / TELEMETRY EVENTS
        # ======================================================================

        # SQM: Failed to start upload with file pattern
        if self.SQM_UPLOAD_FAILED_PATTERN.search(message):
            match = self.SQM_UPLOAD_FAILED_PATTERN.search(message)
            if match:
                file_pattern, flags, hresult, error_name = match.groups()
                return ParsedLogEvent(
                    event_type=WindowsEventType.SQM_UPLOAD_FAILED.value,
                    event_group=EventGroup.ERROR.value,
                    component="CBS",
                    template=self.TEMPLATES["E39"],
                    template_id=template_id_from_csv("E39"),
                    timestamp=timestamp,
                    status="failure",
                    metadata={
                        "file_pattern": file_pattern.strip(),
                        "flags": flags,
                        "hresult": hresult,
                        "error_code": error_name,
                    },
                    parsed_successfully=True,
                    confidence=1.0,
                )

        # SQM: Failed to start standard sample upload
        if self.SQM_UPLOAD_FAILED_ALT.search(message):
            match = self.SQM_UPLOAD_FAILED_ALT.search(message)
            if match:
                hresult, error_name = match.groups()
                return ParsedLogEvent(
                    event_type=WindowsEventType.SQM_UPLOAD_FAILED.value,
                    event_group=EventGroup.ERROR.value,
                    component="CBS",
                    template=self.TEMPLATES["E38"],
                    template_id=template_id_from_csv("E38"),
                    timestamp=timestamp,
                    status="failure",
                    metadata={
                        "hresult": hresult,
                        "error_code": error_name,
                    },
                    parsed_successfully=True,
                    confidence=1.0,
                )

        # ======================================================================
        # SYSTEM / REGISTRY OPERATIONS
        # ======================================================================

        # Loaded Servicing Stack
        if self.LOAD_SERVICING_STACK.search(message):
            match = self.LOAD_SERVICING_STACK.search(message)
            if match:
                stack_version, core_path = match.groups()
                return ParsedLogEvent(
                    event_type=WindowsEventType.LOAD_SERVICING_STACK.value,
                    event_group=EventGroup.SYSTEM.value,
                    component="CBS",
                    template=self.TEMPLATES["E23"],
                    template_id=template_id_from_csv("E23"),
                    timestamp=timestamp,
                    status="success",
                    metadata={
                        "stack_version": stack_version.strip(),
                        "core_path": core_path.strip(),
                    },
                    parsed_successfully=True,
                    confidence=1.0,
                )

        # Loading offline registry hive
        if self.LOAD_REGISTRY.search(message):
            match = self.LOAD_REGISTRY.search(message)
            if match:
                hive_path, registry_key = match.groups()
                return ParsedLogEvent(
                    event_type=WindowsEventType.UNKNOWN.value,  # Fixed: was SYSTEM_INFO
                    event_group=EventGroup.SYSTEM.value,
                    component="CBS",
                    template=self.TEMPLATES["E24"],
                    template_id=template_id_from_csv("E24"),
                    timestamp=timestamp,
                    status="success",
                    metadata={
                        "hive_path": hive_path.strip(),
                        "registry_key": registry_key,
                    },
                    parsed_successfully=True,
                    confidence=0.95,
                )

        # Unloading offline registry hive
        if self.UNLOAD_REGISTRY.search(message):
            match = self.UNLOAD_REGISTRY.search(message)
            if match:
                hive_path = match.group(1)
                return ParsedLogEvent(
                    event_type=WindowsEventType.UNKNOWN.value,  # Fixed: was SYSTEM_INFO
                    event_group=EventGroup.SYSTEM.value,
                    component="CBS",
                    template=self.TEMPLATES["E49"],
                    template_id=template_id_from_csv("E49"),
                    timestamp=timestamp,
                    status="success",
                    metadata={"hive_path": hive_path.strip()},
                    parsed_successfully=True,
                    confidence=0.95,
                )

        # ======================================================================
        # SCAVENGE OPERATIONS
        # ======================================================================

        # Scavenge: Begin
        if self.SCAVENGE_BEGIN.search(message):
            return ParsedLogEvent(
                event_type=WindowsEventType.SCAVENGE.value,
                event_group=EventGroup.SYSTEM.value,
                component="CBS",
                template=self.TEMPLATES["E32"],
                template_id=template_id_from_csv("E32"),
                timestamp=timestamp,
                status="success",
                metadata={},
                parsed_successfully=True,
                confidence=1.0,
            )

        # Scavenge: Completed
        if self.SCAVENGE_COMPLETE.search(message):
            match = self.SCAVENGE_COMPLETE.search(message)
            if match:
                disposition = match.group(1)
                return ParsedLogEvent(
                    event_type=WindowsEventType.SCAVENGE.value,
                    event_group=EventGroup.SYSTEM.value,
                    component="CBS",
                    template=self.TEMPLATES["E33"],
                    template_id=template_id_from_csv("E33"),
                    timestamp=timestamp,
                    status="success",
                    metadata={"disposition": int(disposition)},
                    parsed_successfully=True,
                    confidence=1.0,
                )

        # Scavenge: Starts
        if self.SCAVENGE_START.search(message):
            return ParsedLogEvent(
                event_type=WindowsEventType.SCAVENGE.value,
                event_group=EventGroup.SYSTEM.value,
                component="CBS",
                template=self.TEMPLATES["E34"],
                template_id=template_id_from_csv("E34"),
                timestamp=timestamp,
                status="success",
                metadata={},
                parsed_successfully=True,
                confidence=1.0,
            )

        # ======================================================================
        # ERROR PATTERNS
        # ======================================================================

        # Expecting attribute name error
        if self.EXPECTING_ATTRIBUTE.search(message):
            match = self.EXPECTING_ATTRIBUTE.search(message)
            if match:
                hresult, error_name = match.groups()
                return ParsedLogEvent(
                    event_type=WindowsEventType.MANIFEST_ERROR.value,
                    event_group=EventGroup.ERROR.value,
                    component="CBS",
                    template=self.TEMPLATES["E18"],
                    template_id=template_id_from_csv("E18"),
                    timestamp=timestamp,
                    status="failure",
                    metadata={
                        "hresult": hresult,
                        "error_code": error_name,
                    },
                    parsed_successfully=True,
                    confidence=1.0,
                )

        # Failed to get next element error
        if self.FAILED_GET_ELEMENT.search(message):
            match = self.FAILED_GET_ELEMENT.search(message)
            if match:
                hresult, error_name = match.groups()
                return ParsedLogEvent(
                    event_type=WindowsEventType.PARSE_ERROR.value,
                    event_group=EventGroup.ERROR.value,
                    component="CBS",
                    template=self.TEMPLATES["E20"],
                    template_id=template_id_from_csv("E20"),
                    timestamp=timestamp,
                    status="failure",
                    metadata={
                        "hresult": hresult,
                        "error_code": error_name,
                    },
                    parsed_successfully=True,
                    confidence=1.0,
                )

        # Warning: Unrecognized attribute
        if self.WARNING_UNRECOGNIZED.search(message):
            match = self.WARNING_UNRECOGNIZED.search(message)
            attr_type = match.group(1) if match else "unknown"
            return ParsedLogEvent(
                event_type=WindowsEventType.PARSE_ERROR.value,
                event_group=EventGroup.ERROR.value,
                component="CBS",
                template=self.TEMPLATES["E50"],
                template_id=template_id_from_csv("E50"),
                timestamp=timestamp,
                status="warning",
                metadata={"attribute_type": attr_type},
                parsed_successfully=True,
                confidence=0.9,
            )

        # ======================================================================
        # GENERIC CBS FALLBACK
        # ======================================================================

        # For unmatched CBS events, return a generic system info event
        return ParsedLogEvent(
            event_type=WindowsEventType.UNKNOWN.value,
            event_group=EventGroup.SYSTEM.value,
            component="CBS",
            template="",
            template_id=0,
            timestamp=timestamp,
            status="info",
            metadata={},
            parsed_successfully=False,
            confidence=0.0,
        )

    # ============================================================================
    # CSI (COMPONENT SERVICING INFRASTRUCTURE) PARSER
    # ============================================================================

    def _parse_csi(
        self, message: str, level: str, timestamp: str, log_line: str
    ) -> ParsedLogEvent:
        """
        Parse CSI (Component Servicing Infrastructure) events.
        
        Handles:
        - NT transaction creation and destruction
        - Store initialization and operations
        - WcpInitialize calls
        - Component family keys
        - Performance traces
        """

        # ======================================================================
        # TRANSACTION MANAGEMENT
        # ======================================================================

        # Created NT transaction (seq X) result <result>, handle @<handle>
        if self.TRANSACTION_CREATE.search(message):
            match = self.TRANSACTION_CREATE.search(message)
            if match:
                seq, result, handle = match.groups()
                status = "success" if result == "0x00000000" else "failure"
                return ParsedLogEvent(
                    event_type=WindowsEventType.TRANSACTION_CREATE.value,
                    event_group=EventGroup.TRANSACTION.value,
                    component="CSI",
                    template=self.TEMPLATES["E1"],
                    template_id=template_id_from_csv("E1"),
                    timestamp=timestamp,
                    status=status,
                    metadata={
                        "sequence_number": int(seq),
                        "hresult": result,
                        "handle": handle,
                    },
                    parsed_successfully=True,
                    confidence=1.0,
                )

        # CSI Transaction @<addr> initialized
        if self.TRANSACTION_INITIALIZE.search(message) and "initialize" in message.lower():
            match = self.TRANSACTION_INITIALIZE.search(message)
            if match:
                addr = match.group(1)
                return ParsedLogEvent(
                    event_type=WindowsEventType.TRANSACTION_INITIALIZE.value,
                    event_group=EventGroup.TRANSACTION.value,
                    component="CSI",
                    template=self.TEMPLATES["E10"],
                    template_id=template_id_from_csv("E10"),
                    timestamp=timestamp,
                    status="success",
                    metadata={"transaction_address": addr},
                    parsed_successfully=True,
                    confidence=0.95,
                )

        # CSI Transaction @<addr> destroyed
        if self.TRANSACTION_DESTROY.search(message):
            match = self.TRANSACTION_DESTROY.search(message)
            if match:
                addr = match.group(1)
                return ParsedLogEvent(
                    event_type=WindowsEventType.TRANSACTION_DESTROY.value,
                    event_group=EventGroup.TRANSACTION.value,
                    component="CSI",
                    template=self.TEMPLATES["E9"],
                    template_id=template_id_from_csv("E9"),
                    timestamp=timestamp,
                    status="success",
                    metadata={"transaction_address": addr},
                    parsed_successfully=True,
                    confidence=1.0,
                )

        # ======================================================================
        # STORE INITIALIZATION
        # ======================================================================

        # CSI Store <id> (<addr>) initialized
        if self.CSI_STORE_INITIALIZED.search(message):
            match = self.CSI_STORE_INITIALIZED.search(message)
            if match:
                store_id, addr = match.groups()
                return ParsedLogEvent(
                    event_type=WindowsEventType.UNKNOWN.value,  # Fixed: was SYSTEM_INFO
                    event_group=EventGroup.SYSTEM.value,
                    component="CSI",
                    template=self.TEMPLATES["E4"],
                    template_id=template_id_from_csv("E4"),
                    timestamp=timestamp,
                    status="success",
                    metadata={
                        "store_id": int(store_id),
                        "store_address": addr,
                    },
                    parsed_successfully=True,
                    confidence=1.0,
                )

        # ======================================================================
        # WCP INITIALIZATION
        # ======================================================================

        # WcpInitialize (wcp.dll version X.X.X.X) called
        if self.WCP_INITIALIZE.search(message):
            match = self.WCP_INITIALIZE.search(message)
            if match:
                version = match.group(1)
                return ParsedLogEvent(
                    event_type=WindowsEventType.UNKNOWN.value,  # Fixed: was SYSTEM_INFO
                    event_group=EventGroup.SYSTEM.value,
                    component="CSI",
                    template=self.TEMPLATES["E13"],
                    template_id=template_id_from_csv("E13"),
                    timestamp=timestamp,
                    status="success",
                    metadata={"wcp_version": version},
                    parsed_successfully=True,
                    confidence=0.95,
                )

        # ======================================================================
        # PERFORMANCE TRACES
        # ======================================================================

        # CSI perf trace:
        if "CSI perf trace:" in message:
            return ParsedLogEvent(
                event_type=WindowsEventType.UNKNOWN.value,  # Fixed: was SYSTEM_INFO
                event_group=EventGroup.SYSTEM.value,
                component="CSI",
                template=self.TEMPLATES["E3"],
                template_id=template_id_from_csv("E3"),
                timestamp=timestamp,
                status="info",
                metadata={},
                parsed_successfully=False,
                confidence=0.5,
            )

        # ======================================================================
        # GENERIC CSI FALLBACK
        # ======================================================================

        return ParsedLogEvent(
            event_type=WindowsEventType.UNKNOWN.value,
            event_group=EventGroup.SYSTEM.value,
            component="CSI",
            template="",
            template_id=0,
            timestamp=timestamp,
            status="info",
            metadata={},
            parsed_successfully=False,
            confidence=0.0,
        )
