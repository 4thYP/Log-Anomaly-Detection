#!/usr/bin/env python3
import os
import json
import time
import threading
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
            return {item['log_file']: item['server_id'] for item in config['servers']}
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


def parse_log(filepath, server_id, line, sid=None):
    """Parse a log line - now returns simplified format with full message"""
    
    # Skip SID lines
    if line.startswith('# SID:'):
        return None
    
    # Extract timestamp based on log type
    timestamp = "unknown"
    
    # Try to extract timestamp from different formats
    if '|' in line:
        # For pipe-delimited logs (healthcare, windows, zookeeper)
        parts = line.split('|', 1)
        timestamp = parts[0].strip()
    else:
        # For Linux logs (starts with month)
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        parts = line.split()
        if parts and parts[0] in months and len(parts) >= 3:
            timestamp = f"{parts[0]} {parts[1]} {parts[2]}"
    
    # Return simplified format with FULL original message
    return {
        "timestamp": timestamp,
        "server_type": server_id,
        "sid": sid,
        "message": line,  # The COMPLETE original log line
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

        # Keep only last 1000 entries to prevent file from growing too large
        if len(data) > 1000:
            data = data[-1000:]

        # Write back
        with open(OUTPUT_FILE, "w") as f:
            json.dump(data, f, indent=2)


class LogHandler(FileSystemEventHandler):
    """Handler for log file events"""
    
    def __init__(self, server_map):
        self.server_map = server_map
        self.file_positions = {}  # Store last read position for each file
        # Store SIDs for each server
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
    
    def process_file(self, filepath):
        """Process new lines in a log file"""
        try:
            # Get server ID from config
            log_file_relative = os.path.relpath(filepath, start=os.getcwd())
            server_id = self.server_map.get(log_file_relative, "UNKNOWN")
            
            # Get SID for this file
            sid = self.get_sid_for_file(filepath)
            
            # Get last read position
            last_pos = self.file_positions.get(filepath, 0)
            
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
                            # print(f"Processed: {server_id} - {sid}")
                
                # Update position
                self.file_positions[filepath] = f.tell()
                
        except Exception as e:
            print(f"Error processing file {filepath}: {e}")


def monitor_existing_files(handler):
    """Process any existing content in log files"""
    for filepath in glob.glob(f"{LOG_DIR}/*.log"):
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
    print(f"Loaded {len(server_map)} server configurations")
    for log_file, server_id in server_map.items():
        print(f"  - {server_id}: {log_file}")
    
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
