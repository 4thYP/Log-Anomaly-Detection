# #!/usr/bin/env python3
# """
# Windows Server
# Generates realistic Windows system logs with inner stories
# """
#
# import sys
# import os
# import random
# import time
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#
# from core.base_server import BaseServer
#
# class WindowsServer(BaseServer):
#     def __init__(self):
#         super().__init__(
#             server_type="windows",
#             log_file="windows_server.log",
#             patterns_file="windows_patterns.json"
#         )
#
#         # Windows-specific state
#         self.state.update({
#             'cbs_session': 30546173,
#             'csi_transaction': 1,
#             'reboot_mark': 0,
#             'components': ['CBS', 'CSI', 'TrustedInstaller', 'SQM'],
#             'users': ['SYSTEM', 'TrustedInstaller', 'WindowsUpdateAgent', 'SPP'],
#             'package_counter': 0
#         })
#
#         # Event probabilities based on Windows logs
#         self.event_probabilities = {
#             'cbs_event': 0.35,      # CBS events (Component Based Servicing)
#             'csi_event': 0.30,       # CSI events (Component Servicing Infrastructure)
#             'trusted_installer': 0.15, # TrustedInstaller events
#             'sqm_event': 0.10,        # SQM events
#             'transaction_event': 0.10  # NT transaction events
#         }
#
#         print(f"   🪟 Windows server initialized with {len(self.patterns.get('templates', {}).get('by_frequency', {}))} patterns")
#
#     def generate_timestamp(self):
#         """Generate Windows-style timestamp (2016-09-28 04:30:30)"""
#         year = random.randint(2015, 2024)
#         month = random.randint(1, 12)
#         day = random.randint(1, 28)
#         hour = random.randint(0, 23)
#         minute = random.randint(0, 59)
#         second = random.randint(0, 59)
#         return f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
#
#     def generate_log_line(self):
#         """Generate Windows-specific log with inner story"""
#         rand = random.random()
#         
#         if rand < self.event_probabilities['cbs_event']:
#             return self.generate_cbs_event()
#         elif rand < self.event_probabilities['cbs_event'] + self.event_probabilities['csi_event']:
#             return self.generate_csi_event()
#         elif rand < self.event_probabilities['cbs_event'] + self.event_probabilities['csi_event'] + self.event_probabilities['trusted_installer']:
#             return self.generate_trusted_installer_event()
#         elif rand < self.event_probabilities['cbs_event'] + self.event_probabilities['csi_event'] + self.event_probabilities['trusted_installer'] + self.event_probabilities['sqm_event']:
#             return self.generate_sqm_event()
#         else:
#             return self.generate_transaction_event()
#
#     def generate_cbs_event(self):
#         """Generate CBS (Component Based Servicing) events"""
#         self.state['cbs_session'] += random.randint(1, 100)
#         
#         event_type = random.choice(['startup', 'shutdown', 'package', 'service', 'loading'])
#         
#         if event_type == 'startup':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CBS',
#                 'level': 'Info',
#                 'message': f"Starting TrustedInstaller initialization."
#             }
#         elif event_type == 'shutdown':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CBS',
#                 'level': 'Info',
#                 'message': f"Ending TrustedInstaller main loop."
#             }
#         elif event_type == 'package':
#             self.state['package_counter'] += 1
#             packages = [
#                 'Package_for_KB3121255~31bf3856ad364e35~amd64~~6.1.1.0',
#                 'Package_for_KB3060716~31bf3856ad364e35~amd64~~6.1.1.0',
#                 'Package_for_KB3177186~31bf3856ad364e35~amd64~~6.1.1.1',
#                 'Package_for_KB3086255~31bf3856ad364e35~amd64~~6.1.1.0',
#                 'Package_for_KB3146706~31bf3856ad364e35~amd64~~6.1.1.2'
#             ]
#             package = random.choice(packages)
#             state = random.choice(['112', '80', '0'])
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CBS',
#                 'level': 'Info',
#                 'message': f"Read out cached package applicability for package: {package}, ApplicableState: {state}, CurrentState:{state}"
#             }
#         elif event_type == 'service':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CBS',
#                 'level': 'Info',
#                 'message': f"TrustedInstaller service starts successfully."
#             }
#         else:  # loading
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CBS',
#                 'level': 'Info',
#                 'message': f"Loaded Servicing Stack v6.1.7601.23505 with Core: C:\\Windows\\winsxs\\amd64_microsoft-windows-servicingstack_31bf3856ad364e35_6.1.7601.23505_none_681aa442f6fed7f0\\cbscore.dll"
#             }
#
#     def generate_csi_event(self):
#         """Generate CSI (Component Servicing Infrastructure) events"""
#         self.state['csi_transaction'] += 1
#         
#         event_type = random.choice(['initialize', 'transaction', 'perf', 'wcp'])
#         
#         if event_type == 'initialize':
#             store_id = random.randint(1000000, 50000000)
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CSI',
#                 'level': 'Info',
#                 'message': f"{self.state['csi_transaction']:08d} CSI Store {store_id} (0x{store_id:x}) initialized"
#             }
#         elif event_type == 'transaction':
#             seq = random.randint(1, 10)
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CSI',
#                 'level': 'Info',
#                 'message': f"{self.state['csi_transaction']:08d} Creating NT transaction (seq {seq}), objectname [6]\"(null)\""
#             }
#         elif event_type == 'perf':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CSI',
#                 'level': 'Info',
#                 'message': f"{self.state['csi_transaction']:08d} CSI perf trace:"
#             }
#         else:  # wcp
#             version = f"{random.randint(0,9)}.{random.randint(0,9)}.{random.randint(0,9)}.{random.randint(0,9)}"
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CSI',
#                 'level': 'Info',
#                 'message': f"{self.state['csi_transaction']:08d}@2016/9/27:20:30:31.455 WcpInitialize (wcp.dll version {version}) called (stack @0x7fed806eb5d @0x7fef9fb9b6d @0x7fef9f8358f)"
#             }
#
#     def generate_trusted_installer_event(self):
#         """Generate TrustedInstaller events"""
#         event_type = random.choice(['start', 'stop', 'check', 'nonstart'])
#         
#         if event_type == 'start':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CBS',
#                 'level': 'Info',
#                 'message': f"Starting the TrustedInstaller main loop."
#             }
#         elif event_type == 'stop':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CBS',
#                 'level': 'Info',
#                 'message': f"Ending the TrustedInstaller main loop."
#             }
#         elif event_type == 'check':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CBS',
#                 'level': 'Info',
#                 'message': f"NonStart: Checking to ensure startup processing was not required."
#             }
#         else:
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CBS',
#                 'level': 'Info',
#                 'message': f"No startup processing required, TrustedInstaller service was not set as autostart, or else a reboot is still pending."
#             }
#
#     def generate_sqm_event(self):
#         """Generate SQM events"""
#         event_type = random.choice(['init', 'upload', 'queue', 'fail'])
#         
#         if event_type == 'init':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CBS',
#                 'level': 'Info',
#                 'message': f"SQM: Initializing online with Windows opt-in: False"
#             }
#         elif event_type == 'upload':
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CBS',
#                 'level': 'Info',
#                 'message': f"SQM: Requesting upload of all unsent reports."
#             }
#         elif event_type == 'queue':
#             files = random.randint(0, 10)
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CBS',
#                 'level': 'Info',
#                 'message': f"SQM: Queued {files} file(s) for upload with pattern: C:\\Windows\\servicing\\sqm\\*_all.sqm, flags: 0x6"
#             }
#         else:  # fail
#             self.state['reboot_mark'] += 1
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CBS',
#                 'level': 'Info',
#                 'message': f"SQM: Failed to start standard sample upload. [HRESULT = 0x80004005 - E_FAIL]"
#             }
#
#     def generate_transaction_event(self):
#         """Generate NT transaction events"""
#         seq = random.randint(1, 5)
#         result = "0x00000000"
#         handle = f"@0x{random.randint(100, 1000):x}"
#         
#         if random.random() < 0.5:
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CSI',
#                 'level': 'Info',
#                 'message': f"{self.state['csi_transaction']:08d} Created NT transaction (seq {seq}) result {result}, handle {handle}"
#             }
#         else:
#             return {
#                 'timestamp': self.generate_timestamp(),
#                 'component': 'CSI',
#                 'level': 'Info',
#                 'message': f"{self.state['csi_transaction']:08d} ICSITransaction::Commit calling IStorePendingTransaction::Apply - coldpatching=FALSE applyflags=7"
#             }
#
# if __name__ == "__main__":
#     server = WindowsServer()
#     server.max_logs = 20
#     print("\n" + "="*50)
#     print("🪟 WINDOWS SERVER TEST")
#     print("="*50)
#     server.run()
#     
#     print("\n📄 First 5 generated logs:")
#     print("-"*50)
#     try:
#         # Use the actual log file path from the server
#         with open(server.log_file, 'r') as f:
#             lines = f.readlines()
#             for i, line in enumerate(lines[:5]):
#                 print(f"{i+1}: {line.strip()}")
#     except Exception as e:
#         print(f"Could not read log file: {e}")



#!/usr/bin/env python3
"""
Windows Server
Generates realistic Windows system logs with inner stories
"""

import sys
import os
import random
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.base_server import BaseServer

class WindowsServer(BaseServer):
    def __init__(self):
        super().__init__(
            server_type="windows",
            log_file="windows_server.log",
            patterns_file="windows_patterns.json"
        )

        # ADD DEBUG HERE
        print(f"🔍 DEBUG - Current working directory: {os.getcwd()}")
        print(f"🔍 DEBUG - Log file path from base: {self.log_file}")
        print(f"🔍 DEBUG - Absolute log path: {os.path.abspath(self.log_file)}")
        print(f"🔍 DEBUG - Log directory exists? {os.path.exists(os.path.dirname(self.log_file))}")
        print(f"🔍 DEBUG - Can write to log dir? {os.access(os.path.dirname(self.log_file), os.W_OK)}")

        # Windows-specific state
        self.state.update({
            'cbs_session': 30546173,
            'csi_transaction': 1,
            'reboot_mark': 0,
            'components': ['CBS', 'CSI', 'TrustedInstaller', 'SQM'],
            'users': ['SYSTEM', 'TrustedInstaller', 'WindowsUpdateAgent', 'SPP'],
            'package_counter': 0
        })

        # Event probabilities based on Windows logs
        self.event_probabilities = {
            'cbs_event': 0.35,      # CBS events (Component Based Servicing)
            'csi_event': 0.30,       # CSI events (Component Servicing Infrastructure)
            'trusted_installer': 0.15, # TrustedInstaller events
            'sqm_event': 0.10,        # SQM events
            'transaction_event': 0.10  # NT transaction events
        }

        print(f"   🪟 Windows server initialized with {len(self.patterns.get('templates', {}).get('by_frequency', {}))} patterns")

    def generate_timestamp(self):
        """Generate Windows-style timestamp (2016-09-28 04:30:30)"""
        year = random.randint(2015, 2024)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        return f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"

    def generate_log_line(self):
        """Generate Windows-specific log with inner story"""
        rand = random.random()
        
        if rand < self.event_probabilities['cbs_event']:
            return self.generate_cbs_event()
        elif rand < self.event_probabilities['cbs_event'] + self.event_probabilities['csi_event']:
            return self.generate_csi_event()
        elif rand < self.event_probabilities['cbs_event'] + self.event_probabilities['csi_event'] + self.event_probabilities['trusted_installer']:
            return self.generate_trusted_installer_event()
        elif rand < self.event_probabilities['cbs_event'] + self.event_probabilities['csi_event'] + self.event_probabilities['trusted_installer'] + self.event_probabilities['sqm_event']:
            return self.generate_sqm_event()
        else:
            return self.generate_transaction_event()

    def generate_cbs_event(self):
        """Generate CBS (Component Based Servicing) events"""
        self.state['cbs_session'] += random.randint(1, 100)
        
        event_type = random.choice(['startup', 'shutdown', 'package', 'service', 'loading'])
        
        if event_type == 'startup':
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CBS',
                'level': 'Info',
                'message': f"Starting TrustedInstaller initialization."
            }
        elif event_type == 'shutdown':
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CBS',
                'level': 'Info',
                'message': f"Ending TrustedInstaller main loop."
            }
        elif event_type == 'package':
            self.state['package_counter'] += 1
            packages = [
                'Package_for_KB3121255~31bf3856ad364e35~amd64~~6.1.1.0',
                'Package_for_KB3060716~31bf3856ad364e35~amd64~~6.1.1.0',
                'Package_for_KB3177186~31bf3856ad364e35~amd64~~6.1.1.1',
                'Package_for_KB3086255~31bf3856ad364e35~amd64~~6.1.1.0',
                'Package_for_KB3146706~31bf3856ad364e35~amd64~~6.1.1.2'
            ]
            package = random.choice(packages)
            state = random.choice(['112', '80', '0'])
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CBS',
                'level': 'Info',
                'message': f"Read out cached package applicability for package: {package}, ApplicableState: {state}, CurrentState:{state}"
            }
        elif event_type == 'service':
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CBS',
                'level': 'Info',
                'message': f"TrustedInstaller service starts successfully."
            }
        else:  # loading
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CBS',
                'level': 'Info',
                'message': f"Loaded Servicing Stack v6.1.7601.23505 with Core: C:\\Windows\\winsxs\\amd64_microsoft-windows-servicingstack_31bf3856ad364e35_6.1.7601.23505_none_681aa442f6fed7f0\\cbscore.dll"
            }

    def generate_csi_event(self):
        """Generate CSI (Component Servicing Infrastructure) events"""
        self.state['csi_transaction'] += 1
        
        event_type = random.choice(['initialize', 'transaction', 'perf', 'wcp'])
        
        if event_type == 'initialize':
            store_id = random.randint(1000000, 50000000)
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CSI',
                'level': 'Info',
                'message': f"{self.state['csi_transaction']:08d} CSI Store {store_id} (0x{store_id:x}) initialized"
            }
        elif event_type == 'transaction':
            seq = random.randint(1, 10)
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CSI',
                'level': 'Info',
                'message': f"{self.state['csi_transaction']:08d} Creating NT transaction (seq {seq}), objectname [6]\"(null)\""
            }
        elif event_type == 'perf':
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CSI',
                'level': 'Info',
                'message': f"{self.state['csi_transaction']:08d} CSI perf trace:"
            }
        else:  # wcp
            version = f"{random.randint(0,9)}.{random.randint(0,9)}.{random.randint(0,9)}.{random.randint(0,9)}"
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CSI',
                'level': 'Info',
                'message': f"{self.state['csi_transaction']:08d}@2016/9/27:20:30:31.455 WcpInitialize (wcp.dll version {version}) called (stack @0x7fed806eb5d @0x7fef9fb9b6d @0x7fef9f8358f)"
            }

    def generate_trusted_installer_event(self):
        """Generate TrustedInstaller events"""
        event_type = random.choice(['start', 'stop', 'check', 'nonstart'])
        
        if event_type == 'start':
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CBS',
                'level': 'Info',
                'message': f"Starting the TrustedInstaller main loop."
            }
        elif event_type == 'stop':
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CBS',
                'level': 'Info',
                'message': f"Ending the TrustedInstaller main loop."
            }
        elif event_type == 'check':
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CBS',
                'level': 'Info',
                'message': f"NonStart: Checking to ensure startup processing was not required."
            }
        else:
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CBS',
                'level': 'Info',
                'message': f"No startup processing required, TrustedInstaller service was not set as autostart, or else a reboot is still pending."
            }

    def generate_sqm_event(self):
        """Generate SQM events"""
        event_type = random.choice(['init', 'upload', 'queue', 'fail'])
        
        if event_type == 'init':
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CBS',
                'level': 'Info',
                'message': f"SQM: Initializing online with Windows opt-in: False"
            }
        elif event_type == 'upload':
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CBS',
                'level': 'Info',
                'message': f"SQM: Requesting upload of all unsent reports."
            }
        elif event_type == 'queue':
            files = random.randint(0, 10)
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CBS',
                'level': 'Info',
                'message': f"SQM: Queued {files} file(s) for upload with pattern: C:\\Windows\\servicing\\sqm\\*_all.sqm, flags: 0x6"
            }
        else:  # fail
            self.state['reboot_mark'] += 1
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CBS',
                'level': 'Info',
                'message': f"SQM: Failed to start standard sample upload. [HRESULT = 0x80004005 - E_FAIL]"
            }

    def generate_transaction_event(self):
        """Generate NT transaction events"""
        seq = random.randint(1, 5)
        result = "0x00000000"
        handle = f"@0x{random.randint(100, 1000):x}"
        
        if random.random() < 0.5:
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CSI',
                'level': 'Info',
                'message': f"{self.state['csi_transaction']:08d} Created NT transaction (seq {seq}) result {result}, handle {handle}"
            }
        else:
            return {
                'timestamp': self.generate_timestamp(),
                'component': 'CSI',
                'level': 'Info',
                'message': f"{self.state['csi_transaction']:08d} ICSITransaction::Commit calling IStorePendingTransaction::Apply - coldpatching=FALSE applyflags=7"
            }

if __name__ == "__main__":
    server = WindowsServer()
    server.max_logs = 20
    print("\n" + "="*50)
    print("🪟 WINDOWS SERVER TEST")
    print("="*50)
    server.run()
    
    print("\n📄 First 5 generated logs:")
    print("-"*50)
    try:
        # Use the actual log file path from the server
        with open(server.log_file, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:5]):
                print(f"{i+1}: {line.strip()}")
    except Exception as e:
        print(f"Could not read log file: {e}")
