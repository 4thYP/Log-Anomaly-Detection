import re
from typing import Dict, Optional, List
from app.parsers.base_parser import BaseParser


class LinuxParser(BaseParser):
    """
    Linux System Log Parser
    Handles various log formats from Linux systems including:
    - SSH/SSHD logs
    - Authentication logs
    - System service logs
    - Kernel logs
    - FTP logs
    - Network service logs
    - And more
    """

    # ===== HEADER PATTERN =====
    header_pattern = re.compile(
        r"^(?P<month>\w+) (?P<day>\d+) (?P<time>\d+:\d+:\d+) "
        r"(?P<host>\S+) (?P<process>[^\[]+)(?:\[(?P<pid>\d+)\])?: (?P<message>.*)$"
    )

    # Alternative header pattern for processes without PID
    header_pattern_no_pid = re.compile(
        r"^(?P<month>\w+) (?P<day>\d+) (?P<time>\d+:\d+:\d+) "
        r"(?P<host>\S+) (?P<process>\S+): (?P<message>.*)$"
    )

    # ===== COMMON PATTERNS =====
    ip_pattern = re.compile(r'(?P<ip>\b(?:\d{1,3}\.){3}\d{1,3}\b)')
    hostname_pattern = re.compile(r'rhost=(?P<hostname>[^\s]+)')
    user_pattern = re.compile(r'user=(?P<user>\S+)')
    rhost_pattern = re.compile(r'rhost=(?P<host>[^\s]+)')

    # ===== SSH/SSHD PATTERNS =====
    
    # Authentication failure with user (root, guest, test, etc.)
    auth_failure_pattern = re.compile(
        r'authentication failure;.*?rhost=(?P<host>[^\s]+)(?:\s+user=(?P<user>\S+))?'
    )
    
    # Authentication failure with specific user types
    auth_failure_root = re.compile(r'authentication failure;.*rhost=(?P<host>[^\s]+)\s+user=root')
    auth_failure_guest = re.compile(r'authentication failure;.*rhost=(?P<host>[^\s]+)\s+user=guest')
    auth_failure_test = re.compile(r'authentication failure;.*rhost=(?P<host>[^\s]+)\s+user=test')
    
    # Invalid user / check pass
    invalid_user_pattern = re.compile(r'check pass; user unknown')
    
    # Session management
    session_open_pattern = re.compile(r'session opened for user (?P<user>\S+) by \((?:uid=(?P<uid>\d+)|LOGIN\(uid=(?P<login_uid>\d+)\))\)')
    session_close_pattern = re.compile(r'session closed for user (?P<user>\S+)')
    
    # SSH successful login
    ssh_session_pattern = re.compile(r'session opened for user (?P<user>\S+)')
    
    # ===== FTP PATTERNS =====
    
    # FTP connection
    ftp_connection_pattern = re.compile(
        r'connection from (?P<ip>[\d\.]+)(?:\s+\((?P<hostname>[^)]+)\))? at (?P<date>\w+ \w+ \d+ \d+:\d+:\d+ \d+)'
    )
    
    # Anonymous FTP login
    ftp_anonymous_pattern = re.compile(
        r'ANONYMOUS FTP LOGIN FROM (?P<ip>[\d\.]+),\s+\(anonymous\)'
    )
    
    # FTP timeout
    ftp_timeout_pattern = re.compile(
        r'User unknown timed out after (?P<seconds>\d+) seconds at (?P<date>[^:]+:\d+:\d+:\d+ \d+)'
    )
    
    # ===== SYSTEM SERVICE PATTERNS =====
    
    # Logrotate alerts
    logrotate_alert_pattern = re.compile(r'logrotate: ALERT exited abnormally with \[(?P<code>\d+)\]')
    
    # CUPS service
    cups_shutdown_pattern = re.compile(r'cupsd shutdown succeeded')
    cups_startup_pattern = re.compile(r'cupsd startup succeeded')
    
    # Syslog restart
    syslog_restart_pattern = re.compile(r'syslogd (?P<version>[\d\.]+): restart\.')
    
    # SNMP
    snmp_packet_pattern = re.compile(r'Received SNMP packet\(s\) from (?P<ip>[\d\.]+)')
    
    # ===== KERNEL PATTERNS =====
    
    # Kernel boot messages
    kernel_boot_pattern = re.compile(r'kernel: (?P<kernel_msg>.*)')
    
    # Memory information
    memory_pattern = re.compile(r'(?P<size>\d+)MB (?P<type>HIGHMEM|LOWMEM) available')
    
    # CPU information
    cpu_pattern = re.compile(r'CPU: (?P<cpu_info>.*)')
    
    # BIOS memory map
    bios_e820_pattern = re.compile(r'BIOS-e820: (?P<start>[0-9a-f]+) - (?P<end>[0-9a-f]+) \((?P<type>usable|reserved)\)')
    
    # ===== AUTHENTICATION PATTERNS =====
    
    # Kerberos/klogind authentication
    kerberos_auth_failure = re.compile(
        r'Authentication failed from (?P<ip>[\d\.]+) \((?P<hostname>[^)]+)\): (?P<reason>.*)'
    )
    kerberos_failed = re.compile(r'Kerberos authentication failed')
    
    # GDM authentication
    gdm_auth_failure = re.compile(r'gdm\(pam_unix\)\[\d+\]: authentication failure;.*tty=:0')
    gdm_auth_failed = re.compile(r'Couldn\'t authenticate user')
    
    # ===== NETWORK SERVICE PATTERNS =====
    
    # Named/DNS
    named_notify_pattern = re.compile(r'notify question section contains no SOA')
    
    # Xinetd warnings
    xinetd_warning = re.compile(r'warning: can\'t get client address: Connection reset by peer')
    ftp_getpeername = re.compile(r'getpeername \(ftpd\): Transport endpoint is not connected')
    
    # ===== DEVICE PATTERNS =====
    
    # Udev events
    udev_remove_pattern = re.compile(r'removing device node \'(?P<device>[^\']+)\'')
    udev_create_pattern = re.compile(r'creating device node \'(?P<device>[^\']+)\'')
    
    # ===== SERVICE STARTUP PATTERNS =====
    
    # Various service startup messages
    service_startup_patterns = {
        'portmap': r'portmap startup succeeded',
        'nfslock': r'rpc.statd startup succeeded',
        'rpcidmapd': r'rpc.idmapd startup succeeded',
        'irqbalance': r'irqbalance startup succeeded',
        'random': r'Initializing random number generator:\s+succeeded',
        'network_setting': r'Setting network parameters:\s+succeeded',
        'network_loopback': r'Bringing up loopback interface:\s+succeeded',
        'pcmcia': r'Starting pcmcia:\s+succeeded',
        'bluetooth_hcid': r'hcid startup succeeded',
        'bluetooth_sdpd': r'sdpd startup succeeded',
        'syslog': r'syslogd startup succeeded',
        'klog': r'klogd startup succeeded',
    }
    
    # ===== ROOT LOGIN =====
    root_login_pattern = re.compile(r'ROOT LOGIN ON tty(?P<tty>\d+)')
    
    # ===== EVENT TEMPLATE MAPPING =====
    event_templates = {
        # SSH/SSHD Events
        'auth_failure': 'authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*>',
        'auth_failure_root': 'authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*> user=root',
        'auth_failure_guest': 'authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*> user=guest',
        'auth_failure_test': 'authentication failure; logname= uid=0 euid=0 tty=NODEVssh ruser= rhost=<*> user=test',
        'invalid_user': 'check pass; user unknown',
        'session_open': 'session opened for user <*> by (uid=<*>)',
        'session_close': 'session closed for user <*>',
        
        # FTP Events
        'ftp_connection': 'connection from <*> (<*>) at <*>:<*>:<*>',
        'ftp_anonymous': 'ANONYMOUS FTP LOGIN FROM <*>, (anonymous)',
        'ftp_timeout': 'User unknown timed out after <*> seconds at <*>:<*>:<*> <*>',
        
        # System Service Events
        'logrotate_alert': 'ALERT exited abnormally with [1]',
        'cups_shutdown': 'cupsd shutdown succeeded',
        'cups_startup': 'cupsd startup succeeded',
        'syslog_restart': 'restart.',
        'snmp_packet': 'Received SNMP packet(s) from <*>',
        
        # Kernel Events
        'kernel_boot': 'kernel: <*>',
        'memory_info': '<*> HIGHMEM available.',
        'cpu_info': 'CPU: <*>',
        'bios_e820': 'BIOS-e820: <*> - <*> (<*>)',
        
        # Authentication Events
        'kerberos_auth': 'Authentication failed from <*> (<*>): <*>',
        'kerberos_failed': 'Kerberos authentication failed',
        'gdm_auth_failure': 'authentication failure; logname= uid=0 euid=0 tty=:0 ruser= rhost=',
        'gdm_auth_failed': "Couldn't authenticate user",
        
        # Network Service Events
        'named_notify': 'notify question section contains no SOA',
        'xinetd_warning': "warning: can't get client address: Connection reset by peer",
        'ftp_getpeername': 'getpeername (ftpd): Transport endpoint is not connected',
        
        # Device Events
        'udev_remove': "removing device node '/udev/<*>'",
        'udev_create': "creating device node '/udev/<*>'",
        
        # Service Startup Events
        'service_startup': '<*> startup succeeded',
        'network_setting': 'Setting network parameters: succeeded',
        'network_loopback': 'Bringing up loopback interface: succeeded',
        
        # Root Login
        'root_login': 'ROOT LOGIN ON tty2',
        
        # GPM/Mouse
        'gpm_info': '*** info [mice.c(<*>)]:',
        'gpm_auto': 'imps2: Auto-detected intellimouse PS/<*>',
        
        # Default
        'other': 'other',
    }

    def parse(self, message: str) -> Dict:
        """
        Parse a Linux log message and return structured data
        """
        
        # STEP 1: Parse header
        header_match = self.header_pattern.match(message)
        if not header_match:
            header_match = self.header_pattern_no_pid.match(message)
        
        if not header_match:
            return {
                "event_type": "unknown",
                "template": "unknown",
                "raw_message": message[:200]
            }
        
        header = header_match.groupdict()
        msg = header.get("message", "")
        process = header.get("process", "").strip()
        pid = header.get("pid")
        month = header.get("month")
        day = header.get("day")
        time_val = header.get("time")
        host = header.get("host")
        
        # Initialize result with header info
        result = {
            "timestamp": f"{month} {day} {time_val}",
            "host": host,
            "process": process,
            "pid": pid,
            "message": msg,
        }
        
        # STEP 2: Detect event type based on message content
        
        # Check for kernel messages first (they're often multi-line)
        kernel_match = self.kernel_boot_pattern.match(msg)
        if kernel_match and process == "kernel":
            kernel_msg = kernel_match.group("kernel_msg")
            result["event_type"] = "kernel_message"
            result["kernel_message"] = kernel_msg
            
            # Parse kernel-specific patterns
            if "HIGHMEM" in kernel_msg:
                result["event_type"] = "memory_info"
                result["template"] = self.event_templates['memory_info']
            elif "CPU:" in kernel_msg and "L1 I cache" not in kernel_msg:
                result["event_type"] = "cpu_info"
                result["template"] = self.event_templates['cpu_info']
            elif "BIOS-e820:" in kernel_msg:
                e820_match = self.bios_e820_pattern.search(kernel_msg)
                if e820_match:
                    result["event_type"] = "bios_e820"
                    result["start"] = e820_match.group("start")
                    result["end"] = e820_match.group("end")
                    result["memory_type"] = e820_match.group("type")
                    result["template"] = self.event_templates['bios_e820']
            else:
                result["template"] = "kernel: <*>"
            return result
        
        # SSH Authentication Failures
        if "authentication failure" in msg and "sshd" in process:
            # Check for specific user types
            root_match = self.auth_failure_root.search(msg)
            if root_match:
                result["event_type"] = "auth_failure_root"
                result["ip"] = root_match.group("host")
                result["user"] = "root"
                result["status"] = "failed"
                result["template"] = self.event_templates['auth_failure_root']
                return result
            
            guest_match = self.auth_failure_guest.search(msg)
            if guest_match:
                result["event_type"] = "auth_failure_guest"
                result["ip"] = guest_match.group("host")
                result["user"] = "guest"
                result["status"] = "failed"
                result["template"] = self.event_templates['auth_failure_guest']
                return result
            
            test_match = self.auth_failure_test.search(msg)
            if test_match:
                result["event_type"] = "auth_failure_test"
                result["ip"] = test_match.group("host")
                result["user"] = "test"
                result["status"] = "failed"
                result["template"] = self.event_templates['auth_failure_test']
                return result
            
            # Generic auth failure
            auth_match = self.auth_failure_pattern.search(msg)
            if auth_match:
                result["event_type"] = "auth_failure"
                result["ip"] = auth_match.group("host")
                result["user"] = auth_match.group("user")
                result["status"] = "failed"
                result["template"] = self.event_templates['auth_failure']
                return result
        
        # Invalid user check
        if self.invalid_user_pattern.search(msg):
            result["event_type"] = "invalid_user"
            result["status"] = "failed"
            result["template"] = self.event_templates['invalid_user']
            return result
        
        # Session management
        if "session opened" in msg:
            session_match = self.session_open_pattern.search(msg)
            if session_match:
                result["event_type"] = "session_open"
                result["user"] = session_match.group("user")
                result["uid"] = session_match.group("uid") or session_match.group("login_uid")
                result["status"] = "success"
                result["template"] = self.event_templates['session_open']
                return result
        
        if "session closed" in msg:
            session_match = self.session_close_pattern.search(msg)
            if session_match:
                result["event_type"] = "session_close"
                result["user"] = session_match.group("user")
                result["status"] = "success"
                result["template"] = self.event_templates['session_close']
                return result
        
        # FTP events
        if "ftpd" in process:
            # Anonymous login
            if "ANONYMOUS FTP LOGIN" in msg:
                anon_match = self.ftp_anonymous_pattern.search(msg)
                if anon_match:
                    result["event_type"] = "ftp_anonymous"
                    result["ip"] = anon_match.group("ip")
                    result["template"] = self.event_templates['ftp_anonymous']
                    return result
            
            # Timeout
            if "timed out" in msg:
                timeout_match = self.ftp_timeout_pattern.search(msg)
                if timeout_match:
                    result["event_type"] = "ftp_timeout"
                    result["seconds"] = timeout_match.group("seconds")
                    result["template"] = self.event_templates['ftp_timeout']
                    return result
            
            # Connection
            if "connection from" in msg:
                conn_match = self.ftp_connection_pattern.search(msg)
                if conn_match:
                    result["event_type"] = "ftp_connection"
                    result["ip"] = conn_match.group("ip")
                    result["hostname"] = conn_match.group("hostname")
                    result["template"] = self.event_templates['ftp_connection']
                    return result
            
            # getpeername error
            if "getpeername" in msg:
                result["event_type"] = "ftp_getpeername"
                result["template"] = self.event_templates['ftp_getpeername']
                return result
        
        # System service events
        if "logrotate" in process:
            logrotate_match = self.logrotate_alert_pattern.search(msg)
            if logrotate_match:
                result["event_type"] = "logrotate_alert"
                result["exit_code"] = logrotate_match.group("code")
                result["template"] = self.event_templates['logrotate_alert']
                return result
        
        if "cups" in process:
            if "shutdown" in msg:
                result["event_type"] = "cups_shutdown"
                result["template"] = self.event_templates['cups_shutdown']
                return result
            if "startup" in msg:
                result["event_type"] = "cups_startup"
                result["template"] = self.event_templates['cups_startup']
                return result
        
        if "syslog" in process and "restart" in msg:
            result["event_type"] = "syslog_restart"
            result["template"] = self.event_templates['syslog_restart']
            return result
        
        if "snmpd" in process and "SNMP packet" in msg:
            snmp_match = self.snmp_packet_pattern.search(msg)
            if snmp_match:
                result["event_type"] = "snmp_packet"
                result["ip"] = snmp_match.group("ip")
                result["template"] = self.event_templates['snmp_packet']
                return result
        
        # Authentication events
        if "klogind" in process:
            if "Authentication failed" in msg:
                kerb_match = self.kerberos_auth_failure.search(msg)
                if kerb_match:
                    result["event_type"] = "kerberos_auth"
                    result["ip"] = kerb_match.group("ip")
                    result["hostname"] = kerb_match.group("hostname")
                    result["reason"] = kerb_match.group("reason")
                    result["template"] = self.event_templates['kerberos_auth']
                    return result
            if "Kerberos authentication failed" in msg:
                result["event_type"] = "kerberos_failed"
                result["template"] = self.event_templates['kerberos_failed']
                return result
        
        if "gdm" in process:
            if "authentication failure" in msg:
                result["event_type"] = "gdm_auth_failure"
                result["template"] = self.event_templates['gdm_auth_failure']
                return result
            if "Couldn't authenticate user" in msg:
                result["event_type"] = "gdm_auth_failed"
                result["template"] = self.event_templates['gdm_auth_failed']
                return result
        
        # Network service events
        if "named" in process and "notify question section contains no SOA" in msg:
            result["event_type"] = "named_notify"
            result["template"] = self.event_templates['named_notify']
            return result
        
        if "xinetd" in process and "warning" in msg:
            result["event_type"] = "xinetd_warning"
            result["template"] = self.event_templates['xinetd_warning']
            return result
        
        # Device events
        if "udev" in process:
            remove_match = self.udev_remove_pattern.search(msg)
            if remove_match:
                result["event_type"] = "udev_remove"
                result["device"] = remove_match.group("device")
                result["template"] = self.event_templates['udev_remove']
                return result
            
            create_match = self.udev_create_pattern.search(msg)
            if create_match:
                result["event_type"] = "udev_create"
                result["device"] = create_match.group("device")
                result["template"] = self.event_templates['udev_create']
                return result
        
        # GPM events
        if "gpm" in process:
            if "*** info [mice.c(" in msg:
                result["event_type"] = "gpm_info"
                result["template"] = self.event_templates['gpm_info']
                return result
            if "Auto-detected intellimouse" in msg:
                result["event_type"] = "gpm_auto"
                result["template"] = self.event_templates['gpm_auto']
                return result
        
        # Root login
        if "ROOT LOGIN" in msg:
            root_match = self.root_login_pattern.search(msg)
            result["event_type"] = "root_login"
            result["tty"] = root_match.group("tty") if root_match else "unknown"
            result["template"] = self.event_templates['root_login']
            return result
        
        # Service startup events
        for service, pattern in self.service_startup_patterns.items():
            if re.search(pattern, msg):
                result["event_type"] = "service_startup"
                result["service"] = service
                result["template"] = self.event_templates['service_startup']
                return result
        
        # If no specific pattern matched, return as other
        result["event_type"] = "other"
        result["template"] = msg[:100]  # First 100 chars as template
        
        # Try to extract IP if present
        ip_match = self.ip_pattern.search(msg)
        if ip_match:
            result["ip"] = ip_match.group("ip")
        
        return result
    
    def extract_features(self, parsed_log: Dict) -> Dict:
        """
        Extract features from parsed log for ML model
        """
        features = {
            "timestamp": parsed_log.get("timestamp"),
            "host": parsed_log.get("host"),
            "process": parsed_log.get("process"),
            "event_type": parsed_log.get("event_type"),
            "template_id": None,  # Will be mapped from templates CSV
        }
        
        # Extract numeric features
        if parsed_log.get("event_type") in ["auth_failure", "auth_failure_root", "auth_failure_guest", "auth_failure_test"]:
            features["is_auth_failure"] = 1
            features["severity"] = 7  # High severity for authentication failures
        elif parsed_log.get("event_type") == "invalid_user":
            features["is_invalid_user"] = 1
            features["severity"] = 6
        elif parsed_log.get("event_type") in ["session_open", "session_close"]:
            features["is_session_event"] = 1
            features["severity"] = 2
        elif parsed_log.get("event_type") == "logrotate_alert":
            features["is_system_alert"] = 1
            features["severity"] = 5
        elif parsed_log.get("event_type") == "kernel_message":
            features["is_kernel_event"] = 1
            features["severity"] = 3
        elif parsed_log.get("event_type") == "ftp_connection":
            features["is_ftp_connection"] = 1
            features["severity"] = 4
        elif parsed_log.get("event_type") == "ftp_anonymous":
            features["is_anonymous_ftp"] = 1
            features["severity"] = 8  # Very high severity for anonymous FTP
        elif parsed_log.get("event_type") in ["kerberos_auth", "kerberos_failed"]:
            features["is_kerberos_event"] = 1
            features["severity"] = 6
        else:
            features["severity"] = 1
        
        # Add IP if present (for anomaly detection)
        if parsed_log.get("ip"):
            features["has_ip"] = 1
            # Could add geolocation features later
        else:
            features["has_ip"] = 0
        
        return features
