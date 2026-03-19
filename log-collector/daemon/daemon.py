# #!/usr/bin/env python3
# import os
# import json
# import time
# import threading
# from watchdog.observers import Observer
# from watchdog.events import FileSystemEventHandler
# import glob
#
# LOG_DIR = "logs"
# OUTPUT_FILE = "daemon/daemon.json"
# CONFIG_FILE = "daemon/daemon_config.json"
#
# lock = threading.Lock()
#
#
# def load_config():
#     """Load server configurations"""
#     try:
#         with open(CONFIG_FILE, 'r') as f:
#             config = json.load(f)
#             return {item['log_file']: item['server_id'] for item in config['servers']}
#     except Exception as e:
#         print(f"Error loading config: {e}")
#         return {}
#
#
# def extract_sid_from_file(filepath):
#     """Extract SID from the first line of the log file"""
#     try:
#         with open(filepath, 'r') as f:
#             first_line = f.readline().strip()
#             if first_line.startswith('# SID:'):
#                 sid = first_line.replace('# SID:', '').strip()
#                 print(f"✅ Extracted SID: {sid} from {filepath}")
#                 return sid
#     except Exception as e:
#         print(f"⚠️ Error extracting SID: {e}")
#     return None
#
#
# def parse_log(filepath, server_id, line, sid=None):
#     """Parse a log line - now returns simplified format with full message"""
#     
#     # Skip SID lines
#     if line.startswith('# SID:'):
#         return None
#     
#     # Extract timestamp based on log type
#     timestamp = "unknown"
#     
#     # Try to extract timestamp from different formats
#     if '|' in line:
#         # For pipe-delimited logs (healthcare, windows, zookeeper)
#         parts = line.split('|', 1)
#         timestamp = parts[0].strip()
#     else:
#         # For Linux logs (starts with month)
#         months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
#                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
#         parts = line.split()
#         if parts and parts[0] in months and len(parts) >= 3:
#             timestamp = f"{parts[0]} {parts[1]} {parts[2]}"
#     
#     # Return simplified format with FULL original message
#     return {
#         "timestamp": timestamp,
#         "server_type": server_id,
#         "sid": sid,
#         "message": line,  # The COMPLETE original log line
#         "log_file": os.path.basename(filepath)
#     }
#
#
# def write_log(entry):
#     """Write log entry to daemon.json"""
#     with lock:
#         # Initialize file if it doesn't exist
#         if not os.path.exists(OUTPUT_FILE):
#             os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
#             with open(OUTPUT_FILE, "w") as f:
#                 json.dump([], f, indent=2)
#
#         # Read existing data
#         try:
#             with open(OUTPUT_FILE, "r") as f:
#                 data = json.load(f)
#         except (json.JSONDecodeError, FileNotFoundError):
#             data = []
#
#         # Append new entry
#         data.append(entry)
#
#         # Keep only last 1000 entries to prevent file from growing too large
#         if len(data) > 1000:
#             data = data[-1000:]
#
#         # Write back
#         with open(OUTPUT_FILE, "w") as f:
#             json.dump(data, f, indent=2)
#
#
# class LogHandler(FileSystemEventHandler):
#     """Handler for log file events"""
#     
#     def __init__(self, server_map):
#         self.server_map = server_map
#         self.file_positions = {}  # Store last read position for each file
#         # Store SIDs for each server
#         self.server_sids = {}  # Map log_file to SID
#         
#     def on_modified(self, event):
#         if not event.is_directory and event.src_path.endswith('.log'):
#             self.process_file(event.src_path)
#     
#     def get_sid_for_file(self, filepath):
#         """Get SID for a file, either from cache or by reading the file"""
#         if filepath in self.server_sids:
#             return self.server_sids[filepath]
#         
#         # Try to extract SID from file
#         sid = extract_sid_from_file(filepath)
#         if sid:
#             self.server_sids[filepath] = sid
#             return sid
#         
#         # Fallback
#         return None
#     
#     def process_file(self, filepath):
#         """Process new lines in a log file"""
#         try:
#             # Get server ID from config
#             log_file_relative = os.path.relpath(filepath, start=os.getcwd())
#             server_id = self.server_map.get(log_file_relative, "UNKNOWN")
#             
#             # Get SID for this file
#             sid = self.get_sid_for_file(filepath)
#             
#             # Get last read position
#             last_pos = self.file_positions.get(filepath, 0)
#             
#             # Read new lines
#             with open(filepath, 'r') as f:
#                 f.seek(last_pos)
#                 new_lines = f.readlines()
#                 
#                 for line in new_lines:
#                     line = line.strip()
#                     if line:
#                         parsed = parse_log(filepath, server_id, line, sid)
#                         if parsed:
#                             write_log(parsed)
#                             # Uncomment for debugging
#                             # print(f"Processed: {server_id} - {sid}")
#                 
#                 # Update position
#                 self.file_positions[filepath] = f.tell()
#                 
#         except Exception as e:
#             print(f"Error processing file {filepath}: {e}")
#
#
# def monitor_existing_files(handler):
#     """Process any existing content in log files"""
#     for filepath in glob.glob(f"{LOG_DIR}/*.log"):
#         handler.process_file(filepath)
#
#
# def start_daemon():
#     """Start the monitoring daemon"""
#     print(f"Daemon started. Monitoring directory: {LOG_DIR}")
#     print(f"Absolute path: {os.path.abspath(LOG_DIR)}")
#     print(f"Output file: {OUTPUT_FILE}")
#     
#     # Create logs directory if it doesn't exist
#     os.makedirs(LOG_DIR, exist_ok=True)
#     
#     # Load server configurations
#     server_map = load_config()
#     print(f"Loaded {len(server_map)} server configurations")
#     for log_file, server_id in server_map.items():
#         print(f"  - {server_id}: {log_file}")
#     
#     # Create event handler
#     event_handler = LogHandler(server_map)
#     
#     # Process existing files
#     monitor_existing_files(event_handler)
#     
#     # Set up observer
#     observer = Observer()
#     observer.schedule(event_handler, LOG_DIR, recursive=False)
#     observer.start()
#     
#     print("Monitoring started. Press Ctrl+C to stop.")
#     
#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         observer.stop()
#         print("\nDaemon stopped.")
#     
#     observer.join()
#
#
# if __name__ == "__main__":
#     start_daemon()


#!/usr/bin/env python3
import os
import json
import time
import threading
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import glob

LOG_DIR = "logs"
OUTPUT_FILE = "daemon/daemon.json"
CONFIG_FILE = "daemon/daemon_config.json"

lock = threading.Lock()


def load_config():
    """Load server configurations"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Return mapping of log_file basename to server_id
            mapping = {}
            for item in config['servers']:
                # Store both full path and basename for matching
                full_path = item['log_file']
                basename = os.path.basename(full_path)
                mapping[full_path] = item['server_id']
                mapping[basename] = item['server_id']
                # Also store without .log for pattern matching
                base_without_ext = basename.replace('.log', '')
                mapping[base_without_ext] = item['server_id']
                # Store server type name for pattern matching (healthcare -> HEALTHCARE_SERVER)
                server_type = item['server_id'].replace('_SERVER', '').lower()
                mapping[server_type] = item['server_id']
            print(f"Loaded config mapping: {mapping}")
            return mapping
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}


def extract_sid_from_file(filepath):
    """Extract SID from the first line of the log file"""
    try:
        with open(filepath, 'r') as f:
            first_line = f.readline().strip()
            if first_line.startswith('# SID:'):
                sid = first_line.replace('# SID:', '').strip()
                print(f"✅ Extracted SID: {sid} from {filepath}")
                return sid
    except Exception as e:
        print(f"⚠️ Error extracting SID: {e}")
    return None


def get_server_id_from_file(filepath, server_map):
    """Extract server ID from filename using server_map"""
    filename = os.path.basename(filepath)
    filepath_full = filepath  # Full path
    
    print(f"🔍 Matching file: {filename}")
    
    # Strategy 1: Direct match on full path
    if filepath_full in server_map:
        print(f"   ✅ Matched by full path: {server_map[filepath_full]}")
        return server_map[filepath_full]
    
    # Strategy 2: Direct match on filename
    if filename in server_map:
        print(f"   ✅ Matched by filename: {server_map[filename]}")
        return server_map[filename]
    
    # Strategy 3: Extract base name without instance number
    # e.g., healthcare_1.log -> healthcare
    base_name = re.sub(r'_\d+\.log$', '', filename)  # Remove _1.log
    base_name = re.sub(r'\.log$', '', base_name)      # Remove .log
    
    print(f"   Trying base name: {base_name}")
    
    if base_name in server_map:
        print(f"   ✅ Matched by base name: {server_map[base_name]}")
        return server_map[base_name]
    
    # Strategy 4: Try server type mapping (healthcare -> HEALTHCARE_SERVER)
    for key, server_id in server_map.items():
        if isinstance(key, str) and key.lower() in base_name.lower():
            print(f"   ✅ Matched by partial: {key} -> {server_id}")
            return server_id
    
    print(f"   ❌ No match found, using UNKNOWN")
    return "UNKNOWN"


def parse_log(filepath, server_id, line, sid=None):
    """Parse a log line - returns simplified format with full message"""
    
    # Skip SID lines
    if line.startswith('# SID:'):
        return None
    
    timestamp = "unknown"
    
    # Handle different log formats
    
    # 1. Healthcare format: YYYYMMDD-HH:MM:SS:mmm|component|...
    if '|' in line:
        parts = line.split('|')
        # Check if first part looks like a timestamp (digits and hyphens/colons)
        first_part = parts[0].strip()
        if re.match(r'^\d{8}-\d{2}:\d{2}:\d{2}', first_part):
            timestamp = first_part
        else:
            # Try to find timestamp in other parts
            for part in parts:
                part = part.strip()
                if re.match(r'^\d{8}-\d{2}:\d{2}:\d{2}', part):
                    timestamp = part
                    break
    
    # 2. Linux format: "Jun 14 15:16:01 ..."
    elif re.match(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d+\s+\d{2}:\d{2}:\d{2}', line):
        parts = line.split()
        if len(parts) >= 3:
            timestamp = f"{parts[0]} {parts[1]} {parts[2]}"
    
    # 3. Zookeeper/Windows format: YYYY-MM-DD HH:MM:SS,mmm
    elif re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', line):
        if '|' in line:
            timestamp = line.split('|')[0].strip()
        else:
            # Extract up to the comma/milliseconds
            match = re.match(r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,.]\d+)', line)
            if match:
                timestamp = match.group(1)
            else:
                timestamp = line[:19]  # Just YYYY-MM-DD HH:MM:SS
    
    # Return with FULL original message
    return {
        "timestamp": timestamp,
        "server_type": server_id,
        "sid": sid,
        "message": line.strip(),  # The COMPLETE original log line
        "log_file": os.path.basename(filepath)
    }


def write_log(entry):
    """Write log entry to daemon.json"""
    with lock:
        # Initialize file if it doesn't exist
        if not os.path.exists(OUTPUT_FILE):
            os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
            with open(OUTPUT_FILE, "w") as f:
                json.dump([], f, indent=2)

        # Read existing data
        try:
            with open(OUTPUT_FILE, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            data = []

        # Append new entry
        data.append(entry)

        # Keep only last 10000 entries to prevent file from growing too large
        if len(data) > 10000:
            data = data[-10000:]

        # Write back
        with open(OUTPUT_FILE, "w") as f:
            json.dump(data, f, indent=2)


class LogHandler(FileSystemEventHandler):
    """Handler for log file events"""
    
    def __init__(self, server_map):
        self.server_map = server_map
        self.file_positions = {}  # Store last read position for each file
        self.server_sids = {}  # Map log_file to SID
        
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.log'):
            self.process_file(event.src_path)
    
    def get_sid_for_file(self, filepath):
        """Get SID for a file, either from cache or by reading the file"""
        if filepath in self.server_sids:
            return self.server_sids[filepath]
        
        # Try to extract SID from file
        sid = extract_sid_from_file(filepath)
        if sid:
            self.server_sids[filepath] = sid
            return sid
        
        # Fallback
        return None
    
    def get_server_id(self, filepath):
        """Get server ID for a file"""
        return get_server_id_from_file(filepath, self.server_map)
    
    def process_file(self, filepath):
        """Process new lines in a log file"""
        try:
            # Get server ID from filename
            server_id = self.get_server_id(filepath)
            
            # Get SID for this file
            sid = self.get_sid_for_file(filepath)
            
            # Get last read position
            last_pos = self.file_positions.get(filepath, 0)
            
            # Get file size to check if it's new/truncated
            file_size = os.path.getsize(filepath)
            
            # If file size is smaller than last position, file was truncated
            if file_size < last_pos:
                print(f"⚠️ File {filepath} was truncated, resetting position")
                last_pos = 0
            
            # Read new lines
            with open(filepath, 'r') as f:
                f.seek(last_pos)
                new_lines = f.readlines()
                
                for line in new_lines:
                    line = line.strip()
                    if line:
                        parsed = parse_log(filepath, server_id, line, sid)
                        if parsed:
                            write_log(parsed)
                            # Uncomment for debugging
                            # print(f"Processed: {server_id} - {sid[:10]}... - {line[:50]}")
                
                # Update position
                self.file_positions[filepath] = f.tell()
                
        except Exception as e:
            print(f"Error processing file {filepath}: {e}")


def monitor_existing_files(handler):
    """Process any existing content in log files"""
    for filepath in glob.glob(f"{LOG_DIR}/*.log"):
        print(f"📁 Found existing file: {filepath}")
        handler.process_file(filepath)


def start_daemon():
    """Start the monitoring daemon"""
    print(f"Daemon started. Monitoring directory: {LOG_DIR}")
    print(f"Absolute path: {os.path.abspath(LOG_DIR)}")
    print(f"Output file: {OUTPUT_FILE}")
    
    # Create logs directory if it doesn't exist
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Load server configurations
    server_map = load_config()
    print(f"Loaded {len(server_map)} server configuration mappings")
    
    # Create event handler
    event_handler = LogHandler(server_map)
    
    # Process existing files
    monitor_existing_files(event_handler)
    
    # Set up observer
    observer = Observer()
    observer.schedule(event_handler, LOG_DIR, recursive=False)
    observer.start()
    
    print("Monitoring started. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nDaemon stopped.")
    
    observer.join()


if __name__ == "__main__":
    start_daemon()
