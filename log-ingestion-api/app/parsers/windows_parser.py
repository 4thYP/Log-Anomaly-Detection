import re
from typing import Dict, Optional
from app.parsers.base_parser import BaseParser


class WindowsParser(BaseParser):
    """
    Windows System Log Parser
    Handles Windows CBS (Component-Based Servicing) and CSI (Component Servicing Infrastructure) logs
    """
    
    # ===== HEADER PATTERNS =====
    header_pattern = re.compile(
        r"^(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2}),\s+(?P<level>\w+),\s+(?P<component>\S+),\s+(?P<message>.*)$"
    )
    
    # ===== CSI PATTERNS =====
    
    csi_transaction_created = re.compile(
        r'(?P<seq>\d+) Created NT transaction \(seq (?P<seq_num>\d+)\) result (?P<result>0x[0-9a-fA-F]+), handle @(?P<handle>0x[0-9a-fA-F]+)'
    )
    
    csi_transaction_create = re.compile(
        r'(?P<seq>\d+) Creating NT transaction \(seq (?P<seq_num>\d+)\), objectname \[(?P<obj_len>\d+)\]"(?P<obj_name>[^"]*)"'
    )
    
    csi_perf_trace = re.compile(
        r'(?P<seq>\d+)@(?P<date>\d{4}/\d{1,2}/\d{1,2}):(?P<time>\d{2}:\d{2}:\d{2})\.(?P<ms>\d+) CSI perf trace:'
    )
    
    csi_store_init = re.compile(
        r'(?P<seq>\d+) CSI Store (?P<store>\d+) \((?P<address>0x[0-9a-fA-F]+)\) initialized'
    )
    
    csi_resolve_pending = re.compile(
        r'(?P<seq>\d+) IAdvancedInstallerAwareStore_ResolvePendingTransactions \(call (?P<call>\d+)\) \(flags = (?P<flags>[0-9a-fA-F]+), progress = (?P<progress>[^,]+), phase = (?P<phase>\d+), pdwDisposition = @(?P<disposition>0x[0-9a-fA-F]+)'
    )
    
    csi_commit = re.compile(
        r'(?P<seq>\d+) ICSITransaction::Commit calling IStorePendingTransaction::Apply - coldpatching=(?P<coldpatching>[A-Z]+) applyflags=(?P<applyflags>[0-9a-fA-F]+)'
    )
    
    csi_perform_ops = re.compile(
        r'(?P<seq>\d+) Performing (?P<ops>\d+) operations; (?P<non_lock>\d+) are not lock/unlock and follow:'
    )
    
    csi_store_coherency = re.compile(
        r'(?P<seq>\d+) Store coherency cookie matches last scavenge cookie, skipping scavenge\.'
    )
    
    csi_transaction_destroyed = re.compile(
        r'(?P<seq>\d+)@(?P<date>\d{4}/\d{1,2}/\d{1,2}):(?P<time>\d{2}:\d{2}:\d{2})\.(?P<ms>\d+) CSI Transaction @(?P<address>0x[0-9a-fA-F]+) destroyed'
    )
    
    csi_transaction_init = re.compile(
        r'(?P<seq>\d+)@(?P<date>\d{4}/\d{1,2}/\d{1,2}):(?P<time>\d{2}:\d{2}:\d{2})\.(?P<ms>\d+) CSI Transaction @(?P<address>0x[0-9a-fA-F]+) initialized for deployment engine \{(?P<engine>[^}]+)\} with flags (?P<flags>[0-9a-fA-F]+) and client id \[(?P<client_id_len>\d+)\]"(?P<client_id>[^"]*)/"'
    )
    
    csi_populate_begin = re.compile(
        r'(?P<seq>\d+)@(?P<date>\d{4}/\d{1,2}/\d{1,2}):(?P<time>\d{2}:\d{2}:\d{2})\.(?P<ms>\d+) PopulateComponentFamiliesKey - Begin'
    )
    
    csi_populate_end = re.compile(
        r'(?P<seq>\d+)@(?P<date>\d{4}/\d{1,2}/\d{1,2}):(?P<time>\d{2}:\d{2}:\d{2})\.(?P<ms>\d+) PopulateComponentFamiliesKey - End'
    )
    
    csi_wcp_init = re.compile(
        r'(?P<seq>\d+)@(?P<date>\d{4}/\d{1,2}/\d{1,2}):(?P<time>\d{2}:\d{2}:\d{2})\.(?P<ms>\d+) WcpInitialize \(wcp.dll version (?P<version>[\d\.]+)\) called \(stack @(?P<stack>[^)]+)\)'
    )
    
    # ===== CBS PATTERNS =====
    
    cbs_end_main_loop = re.compile(r'Ending the TrustedInstaller main loop\.')
    cbs_end_finalization = re.compile(r'Ending TrustedInstaller finalization\.')
    cbs_end_initialization = re.compile(r'Ending TrustedInstaller initialization\.')
    
    cbs_expecting_attribute = re.compile(
        r'Expecting attribute name \[HRESULT = (?P<hresult>[^ ]+) - CBS_E_MANIFEST_INVALID_ITEM\]'
    )
    
    cbs_backup_log_failed = re.compile(
        r'Failed to create backup log cab\. \[HRESULT = (?P<hresult>[^ ]+) - ERROR_INVALID_FUNCTION\]'
    )
    
    cbs_failed_get_element = re.compile(
        r'Failed to get next element \[HRESULT = (?P<hresult>[^ ]+) - CBS_E_MANIFEST_INVALID_ITEM\]'
    )
    
    cbs_failed_open_package = re.compile(
        r'Failed to internally open package\. \[HRESULT = (?P<hresult>[^ ]+) - CBS_E_INVALID_PACKAGE\]'
    )
    
    cbs_idle_thread_terminated = re.compile(r'Idle processing thread terminated normally')
    
    cbs_loaded_servicing_stack = re.compile(
        r'Loaded Servicing Stack (?P<version>[\d\.]+) with Core: (?P<path>[^\\]+\\[^\\]+\\[^\\]+\\[^\\]+\\[^\\]+\\[^\\]+\\[^\\]+\\[^\\]+\\[^\\]+)\\(?P<dll>cbscore\.dll)'
    )
    
    cbs_load_offline_hive = re.compile(
        r'Loading offline registry hive: (?P<hive>[^,]+), into registry key \'(?P<key>[^\']+)\' from path \'(?P<path>[^\']+)\'\.'
    )
    
    cbs_no_startup_required = re.compile(
        r'No startup processing required, TrustedInstaller service was not set as autostart, or else a reboot is still pending\.'
    )
    
    cbs_nonstart_check = re.compile(r'NonStart: Checking to ensure startup processing was not required\.')
    cbs_nonstart_success = re.compile(r'NonStart: Success, startup processing not required as expected\.')
    cbs_offline_readonly = re.compile(r'Offline image is: read-only')
    cbs_manifest_caching_disabled = re.compile(r'Disabling manifest caching, because the image is not writeable\.')
    
    cbs_read_cached_package = re.compile(
        r'Read out cached package applicability for package: (?P<package>[^,]+), ApplicableState: (?P<app_state>\d+), CurrentState:(?P<curr_state>\d+)'
    )
    
    cbs_reboot_incremented = re.compile(r'Reboot mark refs incremented to: (?P<count>\d+)')
    cbs_reboot_refs = re.compile(r'Reboot mark refs: (?P<count>\d+)')
    
    cbs_scavenge_begin = re.compile(r'Scavenge: Begin CSI Store')
    cbs_scavenge_completed = re.compile(r'Scavenge: Completed, disposition: (?P<disposition>0x[0-9a-fA-F]+)')
    cbs_scavenge_starts = re.compile(r'Scavenge: Starts')
    
    cbs_session_init = re.compile(
        r'Session: (?P<session_id>\d+)_(?P<session_num>\d+) initialized by client (?P<client>\w+)\.'
    )
    cbs_session_spp = re.compile(
        r'Session: (?P<session_id>\d+)_(?P<session_num>\d+) initialized by client SPP\.'
    )
    
    cbs_sqm_cleanup = re.compile(r'SQM: Cleaning up report files older than (?P<days>\d+) days\.')
    cbs_sqm_upload_failed_std = re.compile(
        r'SQM: Failed to start standard sample upload\. \[HRESULT = (?P<hresult>[^ ]+) - E_FAIL\]'
    )
    cbs_sqm_upload_failed = re.compile(
        r'SQM: Failed to start upload with file pattern: (?P<pattern>[^,]+), flags: (?P<flags>0x[0-9a-fA-F]+) \[HRESULT = (?P<hresult>[^ ]+) - E_FAIL\]'
    )
    cbs_sqm_initializing = re.compile(r'SQM: Initializing online with Windows opt-in: (?P<opt_in>\w+)')
    cbs_sqm_queued = re.compile(
        r'SQM: Queued (?P<count>\d+) file\(s\) for upload with pattern: (?P<pattern>[^,]+), flags: (?P<flags>0x[0-9a-fA-F]+)'
    )
    cbs_sqm_request_upload = re.compile(r'SQM: Requesting upload of all unsent reports\.')
    cbs_sqm_upload_warning = re.compile(
        r'SQM: Warning: Failed to upload all unsent reports\. \[HRESULT = (?P<hresult>[^ ]+) - E_FAIL\]'
    )
    
    cbs_start_main_loop = re.compile(r'Starting the TrustedInstaller main loop\.')
    cbs_start_finalization = re.compile(r'Starting TrustedInstaller finalization\.')
    cbs_start_initialization = re.compile(r'Starting TrustedInstaller initialization\.')
    cbs_startup_thread_terminated = re.compile(r'Startup processing thread terminated normally')
    cbs_service_started = re.compile(r'TrustedInstaller service starts successfully\.')
    
    cbs_unload_offline_hive = re.compile(r'Unloading offline registry hive: (?P<hive>[^,]+)')
    cbs_warning_unrecognized = re.compile(r'Warning: Unrecognized packageExtended attribute\.')
    
    def parse(self, message: str) -> Dict:
        """
        Parse a Windows log message and return structured data
        """
        
        # Parse header
        header_match = self.header_pattern.match(message)
        if not header_match:
            return {
                "event_type": "unknown",
                "template_id": None,
                "raw_message": message[:200]
            }
        
        header = header_match.groupdict()
        msg = header.get("message", "")
        level = header.get("level", "Info")
        component = header.get("component", "Unknown")
        date_str = header.get("date")
        time_str = header.get("time")
        
        timestamp = f"{date_str} {time_str}"
        
        result = {
            "timestamp": timestamp,
            "level": level,
            "component": component,
            "message": msg,
        }
        
        # ===== CSI Transaction Events =====
        
        if "Created NT transaction" in msg:
            match = self.csi_transaction_created.search(msg)
            if match:
                result["event_type"] = "csi_transaction_created"
                result["template_id"] = "E1"
                result["sequence"] = match.group("seq")
                result["transaction_seq"] = match.group("seq_num")
                result["result"] = match.group("result")
                result["handle"] = match.group("handle")
                return result
        
        if "Creating NT transaction" in msg:
            match = self.csi_transaction_create.search(msg)
            if match:
                result["event_type"] = "csi_transaction_create"
                result["template_id"] = "E2"
                result["sequence"] = match.group("seq")
                result["transaction_seq"] = match.group("seq_num")
                result["object_name"] = match.group("obj_name")
                return result
        
        if "CSI perf trace:" in msg:
            match = self.csi_perf_trace.search(msg)
            if match:
                result["event_type"] = "csi_perf_trace"
                result["template_id"] = "E3"
                result["sequence"] = match.group("seq")
                return result
        
        if "CSI Store" in msg and "initialized" in msg:
            match = self.csi_store_init.search(msg)
            if match:
                result["event_type"] = "csi_store_initialized"
                result["template_id"] = "E4"
                result["sequence"] = match.group("seq")
                result["store_size"] = match.group("store")
                result["store_address"] = match.group("address")
                return result
        
        if "IAdvancedInstallerAwareStore_ResolvePendingTransactions" in msg:
            match = self.csi_resolve_pending.search(msg)
            if match:
                result["event_type"] = "csi_resolve_pending"
                result["template_id"] = "E5"
                result["sequence"] = match.group("seq")
                result["call_number"] = match.group("call")
                result["flags"] = match.group("flags")
                result["phase"] = match.group("phase")
                return result
        
        if "ICSITransaction::Commit" in msg:
            match = self.csi_commit.search(msg)
            if match:
                result["event_type"] = "csi_commit"
                result["template_id"] = "E6"
                result["sequence"] = match.group("seq")
                result["coldpatching"] = match.group("coldpatching")
                result["applyflags"] = match.group("applyflags")
                return result
        
        if "Performing" in msg and "operations" in msg:
            match = self.csi_perform_ops.search(msg)
            if match:
                result["event_type"] = "csi_perform_ops"
                result["template_id"] = "E7"
                result["sequence"] = match.group("seq")
                result["operations_count"] = match.group("ops")
                result["non_lock_operations"] = match.group("non_lock")
                return result
        
        if "Store coherency cookie matches" in msg:
            match = self.csi_store_coherency.search(msg)
            if match:
                result["event_type"] = "csi_store_coherency"
                result["template_id"] = "E8"
                result["sequence"] = match.group("seq")
                return result
        
        if "CSI Transaction @0x" in msg and "destroyed" in msg:
            match = self.csi_transaction_destroyed.search(msg)
            if match:
                result["event_type"] = "csi_transaction_destroyed"
                result["template_id"] = "E9"
                result["sequence"] = match.group("seq")
                result["transaction_address"] = match.group("address")
                return result
        
        if "CSI Transaction @0x" in msg and "initialized" in msg and "deployment engine" in msg:
            match = self.csi_transaction_init.search(msg)
            if match:
                result["event_type"] = "csi_transaction_initialized"
                result["template_id"] = "E10"
                result["sequence"] = match.group("seq")
                result["transaction_address"] = match.group("address")
                result["deployment_engine"] = match.group("engine")
                result["flags"] = match.group("flags")
                result["client_id"] = match.group("client_id")
                return result
        
        if "PopulateComponentFamiliesKey - Begin" in msg:
            match = self.csi_populate_begin.search(msg)
            if match:
                result["event_type"] = "csi_populate_begin"
                result["template_id"] = "E11"
                result["sequence"] = match.group("seq")
                return result
        
        if "PopulateComponentFamiliesKey - End" in msg:
            match = self.csi_populate_end.search(msg)
            if match:
                result["event_type"] = "csi_populate_end"
                result["template_id"] = "E12"
                result["sequence"] = match.group("seq")
                return result
        
        if "WcpInitialize" in msg:
            match = self.csi_wcp_init.search(msg)
            if match:
                result["event_type"] = "csi_wcp_init"
                result["template_id"] = "E13"
                result["sequence"] = match.group("seq")
                result["wcp_version"] = match.group("version")
                return result
        
        # ===== CBS Service Events =====
        
        if "Disabling manifest caching" in msg:
            result["event_type"] = "cbs_manifest_caching_disabled"
            result["template_id"] = "E14"
            return result
        
        if "Ending the TrustedInstaller main loop" in msg:
            result["event_type"] = "cbs_end_main_loop"
            result["template_id"] = "E15"
            return result
        
        if "Ending TrustedInstaller finalization" in msg:
            result["event_type"] = "cbs_end_finalization"
            result["template_id"] = "E16"
            return result
        
        if "Ending TrustedInstaller initialization" in msg:
            result["event_type"] = "cbs_end_initialization"
            result["template_id"] = "E17"
            return result
        
        if "Expecting attribute name" in msg:
            match = self.cbs_expecting_attribute.search(msg)
            if match:
                result["event_type"] = "cbs_expecting_attribute"
                result["template_id"] = "E18"
                result["hresult"] = match.group("hresult")
                return result
        
        if "Failed to create backup log cab" in msg:
            match = self.cbs_backup_log_failed.search(msg)
            if match:
                result["event_type"] = "cbs_backup_log_failed"
                result["template_id"] = "E19"
                result["hresult"] = match.group("hresult")
                return result
        
        if "Failed to get next element" in msg:
            match = self.cbs_failed_get_element.search(msg)
            if match:
                result["event_type"] = "cbs_failed_get_element"
                result["template_id"] = "E20"
                result["hresult"] = match.group("hresult")
                return result
        
        if "Failed to internally open package" in msg:
            match = self.cbs_failed_open_package.search(msg)
            if match:
                result["event_type"] = "cbs_failed_open_package"
                result["template_id"] = "E21"
                result["hresult"] = match.group("hresult")
                return result
        
        if "Idle processing thread terminated normally" in msg:
            result["event_type"] = "cbs_idle_thread_terminated"
            result["template_id"] = "E22"
            return result
        
        if "Loaded Servicing Stack" in msg:
            match = self.cbs_loaded_servicing_stack.search(msg)
            if match:
                result["event_type"] = "cbs_loaded_servicing_stack"
                result["template_id"] = "E23"
                result["stack_version"] = match.group("version")
                result["core_path"] = match.group("path")
                result["dll_name"] = match.group("dll")
                return result
        
        if "Loading offline registry hive" in msg:
            match = self.cbs_load_offline_hive.search(msg)
            if match:
                result["event_type"] = "cbs_load_offline_hive"
                result["template_id"] = "E24"
                result["hive_name"] = match.group("hive")
                result["registry_key"] = match.group("key")
                result["registry_path"] = match.group("path")
                return result
        
        if "No startup processing required" in msg:
            result["event_type"] = "cbs_no_startup_required"
            result["template_id"] = "E25"
            return result
        
        if "NonStart: Checking to ensure startup processing was not required" in msg:
            result["event_type"] = "cbs_nonstart_check"
            result["template_id"] = "E26"
            return result
        
        if "NonStart: Success, startup processing not required as expected" in msg:
            result["event_type"] = "cbs_nonstart_success"
            result["template_id"] = "E27"
            return result
        
        if "Offline image is: read-only" in msg:
            result["event_type"] = "cbs_offline_readonly"
            result["template_id"] = "E28"
            return result
        
        if "Read out cached package applicability" in msg:
            match = self.cbs_read_cached_package.search(msg)
            if match:
                result["event_type"] = "cbs_read_cached_package"
                result["template_id"] = "E29"
                result["package_name"] = match.group("package")
                result["applicable_state"] = match.group("app_state")
                result["current_state"] = match.group("curr_state")
                return result
        
        if "Reboot mark refs incremented to:" in msg:
            match = self.cbs_reboot_incremented.search(msg)
            if match:
                result["event_type"] = "cbs_reboot_incremented"
                result["template_id"] = "E30"
                result["count"] = match.group("count")
                return result
        
        if "Reboot mark refs:" in msg:
            match = self.cbs_reboot_refs.search(msg)
            if match:
                result["event_type"] = "cbs_reboot_refs"
                result["template_id"] = "E31"
                result["count"] = match.group("count")
                return result
        
        if "Scavenge: Begin CSI Store" in msg:
            result["event_type"] = "cbs_scavenge_begin"
            result["template_id"] = "E32"
            return result
        
        if "Scavenge: Completed" in msg:
            match = self.cbs_scavenge_completed.search(msg)
            if match:
                result["event_type"] = "cbs_scavenge_completed"
                result["template_id"] = "E33"
                result["disposition"] = match.group("disposition")
                return result
        
        if "Scavenge: Starts" in msg:
            result["event_type"] = "cbs_scavenge_starts"
            result["template_id"] = "E34"
            return result
        
        if "Session:" in msg and "initialized by client SPP" in msg:
            match = self.cbs_session_spp.search(msg)
            if match:
                result["event_type"] = "cbs_session_spp"
                result["template_id"] = "E35"
                result["session_id"] = match.group("session_id")
                result["session_num"] = match.group("session_num")
                return result
        
        if "Session:" in msg and "initialized by client WindowsUpdateAgent" in msg:
            match = self.cbs_session_init.search(msg)
            if match:
                result["event_type"] = "cbs_session_init"
                result["template_id"] = "E36"
                result["session_id"] = match.group("session_id")
                result["session_num"] = match.group("session_num")
                result["client"] = match.group("client")
                return result
        
        if "SQM: Cleaning up report files older than" in msg:
            match = self.cbs_sqm_cleanup.search(msg)
            if match:
                result["event_type"] = "cbs_sqm_cleanup"
                result["template_id"] = "E37"
                result["days"] = match.group("days")
                return result
        
        if "SQM: Failed to start standard sample upload" in msg:
            match = self.cbs_sqm_upload_failed_std.search(msg)
            if match:
                result["event_type"] = "cbs_sqm_failed_std_upload"
                result["template_id"] = "E38"
                result["hresult"] = match.group("hresult")
                return result
        
        if "SQM: Failed to start upload with file pattern:" in msg:
            match = self.cbs_sqm_upload_failed.search(msg)
            if match:
                result["event_type"] = "cbs_sqm_failed_upload"
                result["template_id"] = "E39"
                result["pattern"] = match.group("pattern")
                result["flags"] = match.group("flags")
                result["hresult"] = match.group("hresult")
                return result
        
        if "SQM: Initializing online with Windows opt-in:" in msg:
            match = self.cbs_sqm_initializing.search(msg)
            if match:
                result["event_type"] = "cbs_sqm_initializing"
                result["template_id"] = "E40"
                result["opt_in"] = match.group("opt_in")
                return result
        
        if "SQM: Queued" in msg and "file(s) for upload" in msg:
            match = self.cbs_sqm_queued.search(msg)
            if match:
                result["event_type"] = "cbs_sqm_queued"
                result["template_id"] = "E41"
                result["file_count"] = match.group("count")
                result["pattern"] = match.group("pattern")
                result["flags"] = match.group("flags")
                return result
        
        if "SQM: Requesting upload of all unsent reports" in msg:
            result["event_type"] = "cbs_sqm_request_upload"
            result["template_id"] = "E42"
            return result
        
        if "SQM: Warning: Failed to upload all unsent reports" in msg:
            match = self.cbs_sqm_upload_warning.search(msg)
            if match:
                result["event_type"] = "cbs_sqm_upload_warning"
                result["template_id"] = "E43"
                result["hresult"] = match.group("hresult")
                return result
        
        if "Starting the TrustedInstaller main loop" in msg:
            result["event_type"] = "cbs_start_main_loop"
            result["template_id"] = "E44"
            return result
        
        if "Starting TrustedInstaller finalization" in msg:
            result["event_type"] = "cbs_start_finalization"
            result["template_id"] = "E45"
            return result
        
        if "Starting TrustedInstaller initialization" in msg:
            result["event_type"] = "cbs_start_initialization"
            result["template_id"] = "E46"
            return result
        
        if "Startup processing thread terminated normally" in msg:
            result["event_type"] = "cbs_startup_thread_terminated"
            result["template_id"] = "E47"
            return result
        
        if "TrustedInstaller service starts successfully" in msg:
            result["event_type"] = "cbs_service_started"
            result["template_id"] = "E48"
            return result
        
        if "Unloading offline registry hive" in msg:
            match = self.cbs_unload_offline_hive.search(msg)
            if match:
                result["event_type"] = "cbs_unload_offline_hive"
                result["template_id"] = "E49"
                result["hive_name"] = match.group("hive")
                return result
        
        if "Warning: Unrecognized packageExtended attribute" in msg:
            result["event_type"] = "cbs_warning_unrecognized"
            result["template_id"] = "E50"
            return result
        
        # Default
        result["event_type"] = "other"
        result["template_id"] = None
        
        return result
