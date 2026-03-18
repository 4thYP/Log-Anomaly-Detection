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


def parse_log(filepath, server_id, line):
    """Parse a log line into JSON format - handles different log types"""
    
    # List of month abbreviations for Linux log detection
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    parts = line.split()
    
    # Check if it's a Linux log (starts with month)
    if parts and parts[0] in months:
        # Linux format: "Jun 14 15:16:01 combo sshd(pam_unix)[19939]: message"
        if len(parts) >= 4:
            timestamp = f"{parts[0]} {parts[1]} {parts[2]}"
            component = parts[3]  # "combo" or service name
            
            # The rest is the message (might contain ":")
            message_parts = parts[4:]
            message = " ".join(message_parts)
            
            return {
                "timestamp": timestamp,
                "level": component,
                "server_id": server_id,
                "log_file": os.path.basename(filepath),
                "message": message
            }
    
    # Check if it's a Zookeeper log (has | delimiter with component that may contain colon)
    elif '|' in line:
        pipe_parts = line.split('|', 2)
        if len(pipe_parts) >= 3:
            timestamp = pipe_parts[0].strip()
            component = pipe_parts[1].strip()
            message = pipe_parts[2].strip()
            
            return {
                "timestamp": timestamp,
                "level": component,
                "server_id": server_id,
                "log_file": os.path.basename(filepath),
                "message": message
            }
    
    # Check if it's a Windows log (starts with date like "2016-09-28" and has comma)
    elif len(parts) >= 3 and parts[0][0].isdigit() and '-' in parts[0] and ',' in line:
        # Windows format: "2016-09-28 04:30:30, Info                  CBS    message"
        if ',' in line:
            # Split at the first comma to separate timestamp from rest
            timestamp_part, rest = line.split(',', 1)
            
            # Rest usually has format: " Info                  CBS    message"
            rest_parts = rest.strip().split()
            if len(rest_parts) >= 2:
                level = rest_parts[0]  # "Info", "Warning", "Error"
                component = rest_parts[1]  # "CBS", "CSI", etc.
                
                # Message is everything after component
                message_start = rest.find(component) + len(component)
                message = rest[message_start:].strip()
                
                return {
                    "timestamp": timestamp_part.strip(),
                    "level": level,
                    "server_id": server_id,
                    "log_file": os.path.basename(filepath),
                    "message": f"{component} {message}"
                }
    
    # Healthcare format (or other formats with | delimiter) - fallback
    parts = [p.strip() for p in line.split("|")]
    
    if len(parts) >= 3:
        timestamp = parts[0]
        level = parts[1]
        message = " | ".join(parts[2:])
        
        return {
            "timestamp": timestamp,
            "level": level,
            "server_id": server_id,
            "log_file": os.path.basename(filepath),
            "message": message
        }
    
    # If we can't parse, return a generic entry
    return {
        "timestamp": "unknown",
        "level": "unknown",
        "server_id": server_id,
        "log_file": os.path.basename(filepath),
        "message": line
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
        
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.log'):
            self.process_file(event.src_path)
    
    def process_file(self, filepath):
        """Process new lines in a log file"""
        try:
            # Get server ID from config
            log_file_relative = os.path.relpath(filepath, start=os.getcwd())
            server_id = self.server_map.get(log_file_relative, "UNKNOWN")
            
            # Get last read position
            last_pos = self.file_positions.get(filepath, 0)
            
            # Read new lines
            with open(filepath, 'r') as f:
                f.seek(last_pos)
                new_lines = f.readlines()
                
                for line in new_lines:
                    line = line.strip()
                    if line:
                        parsed = parse_log(filepath, server_id, line)
                        if parsed:
                            write_log(parsed)
                            # Uncomment for debugging
                            # print(f"Processed: {server_id} - {parsed['level']} - {parsed['message'][:50]}...")
                
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
