#!/usr/bin/env python3
"""
Clean up script - clears all log files and daemon.json
Run this between tests to start fresh
"""

import os
import glob

def clean():
    print("🧹 Clearing log files...")
    
    # Get the log-collector directory (where this script is)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Clear all .log files in the logs directory (make them empty)
    logs_dir = os.path.join(base_dir, "logs")
    if os.path.exists(logs_dir):
        log_files = glob.glob(os.path.join(logs_dir, "*.log"))
        for log_file in log_files:
            try:
                # Open in write mode to truncate (empty) the file
                open(log_file, 'w').close()
                print(f"   ✅ Cleared: {os.path.basename(log_file)}")
            except Exception as e:
                print(f"   ❌ Error clearing {log_file}: {e}")
    else:
        print("   ⚠️  logs directory not found")
    
    # 2. Clear daemon.json (make it empty array)
    daemon_json = os.path.join(base_dir, "daemon", "daemon.json")
    if os.path.exists(daemon_json):
        try:
            with open(daemon_json, 'w') as f:
                f.write("[]")
            print("   ✅ Reset daemon/daemon.json to []")
        except Exception as e:
            print(f"   ❌ Error resetting daemon.json: {e}")
    else:
        print("   ⚠️  daemon/daemon.json not found")
    
    # 3. Also clear any log files in module2_generator/servers (just in case)
    servers_dir = os.path.join(base_dir, "module2_generator", "servers")
    if os.path.exists(servers_dir):
        log_files = glob.glob(os.path.join(servers_dir, "*.log"))
        for log_file in log_files:
            try:
                open(log_file, 'w').close()
                print(f"   ✅ Cleared stray: {os.path.basename(log_file)}")
            except:
                pass
    
    # 4. Clear any zookeeper log files that might be elsewhere
    zookeeper_logs = glob.glob(os.path.join(base_dir, "**", "zookeeper_server.log"), recursive=True)
    for log_file in zookeeper_logs:
        if log_file not in log_files:  # Avoid double-counting
            try:
                open(log_file, 'w').close()
                print(f"   ✅ Cleared: {os.path.basename(log_file)}")
            except:
                pass
    
    print("\n✨ Clean up complete! All files are now empty.")

if __name__ == "__main__":
    clean()
