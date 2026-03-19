# #!/usr/bin/env python3
# """
# Clean up script - completely resets the system for a fresh start
# Run this between tests to clear ALL generated data
# """
#
# import os
# import glob
# import json
#
# def clean():
#     print("🧹 Starting fresh cleanup...")
#     print("="*50)
#     
#     # Get the log-collector directory (where this script is)
#     base_dir = os.path.dirname(os.path.abspath(__file__))
#     
#     # 1. Clear all .log files in the logs directory
#     print("\n📁 Clearing log files...")
#     logs_dir = os.path.join(base_dir, "logs")
#     if os.path.exists(logs_dir):
#         log_files = glob.glob(os.path.join(logs_dir, "*.log"))
#         for log_file in log_files:
#             try:
#                 # Open in write mode to truncate (empty) the file
#                 open(log_file, 'w').close()
#                 print(f"   ✅ Cleared: {os.path.basename(log_file)}")
#             except Exception as e:
#                 print(f"   ❌ Error clearing {log_file}: {e}")
#     else:
#         print("   ⚠️  logs directory not found")
#     
#     # 2. Clear daemon.json (make it empty array)
#     print("\n📁 Resetting daemon/daemon.json...")
#     daemon_json = os.path.join(base_dir, "daemon", "daemon.json")
#     if os.path.exists(daemon_json):
#         try:
#             with open(daemon_json, 'w') as f:
#                 f.write("[]")
#             print("   ✅ Reset daemon/daemon.json to []")
#         except Exception as e:
#             print(f"   ❌ Error resetting daemon.json: {e}")
#     else:
#         print("   ⚠️  daemon/daemon.json not found")
#     
#     # 3. RESET server_sids.json - COMPLETELY FRESH!
#     print("\n🔑 Resetting server_sids.json (removing ALL SID history)...")
#     sid_file = os.path.join(base_dir, "server_sids.json")
#     
#     # Create a fresh SID registry with only counters reset to 0
#     fresh_sid_registry = {
#         # Reset all counters to 0 for fresh start
#         "HEALTHCARE_counter": 0,
#         "LINUX_counter": 0,
#         "WINDOWS_counter": 0,
#         "ZOOKEEPER_counter": 0,
#         "DB_SERVER_counter": 0,
#         "API_SERVER_counter": 0,
#         "AUTH_SERVER_counter": 0,
#         "INFRA_SERVER_counter": 0,
#         "HPC_counter": 0,
#         # Empty mapping for SIDs (will be regenerated)
#         "_comment": "Fresh registry - all counters reset to 0"
#     }
#     
#     try:
#         with open(sid_file, 'w') as f:
#             json.dump(fresh_sid_registry, f, indent=2)
#         print(f"   ✅ Reset {sid_file} with all counters = 0")
#         print(f"   📋 New registry structure:")
#         for key in fresh_sid_registry:
#             if not key.startswith('_'):
#                 print(f"      • {key}: 0")
#     except Exception as e:
#         print(f"   ❌ Error resetting server_sids.json: {e}")
#     
#     # 4. Also clear any stray log files in module directories
#     print("\n📁 Checking for stray log files...")
#     
#     # Module 2 servers directory
#     servers_dir = os.path.join(base_dir, "module2_generator", "servers")
#     if os.path.exists(servers_dir):
#         stray_logs = glob.glob(os.path.join(servers_dir, "*.log"))
#         for log_file in stray_logs:
#             try:
#                 open(log_file, 'w').close()
#                 print(f"   ✅ Cleared stray: {os.path.basename(log_file)}")
#             except:
#                 pass
#     
#     # Any zookeeper logs elsewhere
#     zookeeper_logs = glob.glob(os.path.join(base_dir, "**", "zookeeper_server.log"), recursive=True)
#     for log_file in zookeeper_logs:
#         if log_file not in stray_logs:  # Avoid double-counting
#             try:
#                 open(log_file, 'w').close()
#                 print(f"   ✅ Cleared: {os.path.basename(log_file)}")
#             except:
#                 pass
#     
#     # 5. OPTIONAL: Clear the daemon's file position tracking
#     #    (if you want to force re-reading all logs from beginning)
#     print("\n⚙️  Additional cleanup options:")
#     clear_positions = input("   Clear daemon file positions? (y/N): ").lower()
#     if clear_positions == 'y':
#         # The daemon tracks positions in memory only, so restarting it will reset
#         # But we can also delete any position cache files if you create them
#         print("   ✅ Daemon will reset positions on next start")
#     
#     print("\n" + "="*50)
#     print("✨ COMPLETE CLEANUP FINISHED!")
#     print("="*50)
#     print("\n📊 Current state:")
#     print("   • All log files are empty")
#     print("   • daemon.json is reset to []")
#     print("   • server_sids.json has ALL counters = 0")
#     print("   • System is ready for a FRESH START!")
#     print("\n🚀 Run './run.py' to start fresh!")
#
# def quick_clean():
#     """Quick clean without prompts - for scripting"""
#     print("🧹 Quick cleaning...")
#     
#     base_dir = os.path.dirname(os.path.abspath(__file__))
#     
#     # Clear logs
#     logs_dir = os.path.join(base_dir, "logs")
#     if os.path.exists(logs_dir):
#         for log_file in glob.glob(os.path.join(logs_dir, "*.log")):
#             open(log_file, 'w').close()
#     
#     # Reset daemon.json
#     daemon_json = os.path.join(base_dir, "daemon", "daemon.json")
#     if os.path.exists(daemon_json):
#         with open(daemon_json, 'w') as f:
#             f.write("[]")
#     
#     # Reset SID registry
#     sid_file = os.path.join(base_dir, "server_sids.json")
#     fresh_registry = {
#         "HEALTHCARE_counter": 0,
#         "LINUX_counter": 0,
#         "WINDOWS_counter": 0,
#         "ZOOKEEPER_counter": 0,
#         "DB_SERVER_counter": 0,
#         "API_SERVER_counter": 0,
#         "AUTH_SERVER_counter": 0,
#         "INFRA_SERVER_counter": 0,
#         "HPC_counter": 0
#     }
#     with open(sid_file, 'w') as f:
#         json.dump(fresh_registry, f, indent=2)
#     
#     print("✅ Quick clean complete!")
#
# if __name__ == "__main__":
#     # Check for quick clean flag
#     import sys
#     if len(sys.argv) > 1 and sys.argv[1] == "--quick":
#         quick_clean()
#     else:
#         clean()


#!/usr/bin/env python3
"""
Clean up script - resets all generated files
Run this between tests to start fresh
"""

import os
import glob
import json

def clean():
    print("🧹 Cleaning up generated files...")
    
    # Get the base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Delete all .log files in logs directory
    logs_dir = os.path.join(base_dir, "logs")
    if os.path.exists(logs_dir):
        log_files = glob.glob(os.path.join(logs_dir, "*.log"))
        for log_file in log_files:
            try:
                os.remove(log_file)
                print(f"   ✅ Deleted: logs/{os.path.basename(log_file)}")
            except Exception as e:
                print(f"   ❌ Error deleting {log_file}: {e}")
    else:
        print("   ⚠️  logs directory not found")
    
    # 2. RESET daemon.json to [] (instead of deleting)
    daemon_json = os.path.join(base_dir, "daemon", "daemon.json")
    if os.path.exists(daemon_json):
        try:
            with open(daemon_json, 'w') as f:
                json.dump([], f, indent=2)
            print(f"   ✅ Reset daemon/daemon.json to []")
        except Exception as e:
            print(f"   ❌ Error resetting daemon.json: {e}")
    else:
        # Create directory if it doesn't exist
        os.makedirs(os.path.join(base_dir, "daemon"), exist_ok=True)
        with open(daemon_json, 'w') as f:
            json.dump([], f, indent=2)
        print(f"   ✅ Created daemon/daemon.json with []")
    
    # 3. Delete server_sids.json
    sid_file = os.path.join(base_dir, "server_sids.json")
    if os.path.exists(sid_file):
        try:
            os.remove(sid_file)
            print(f"   ✅ Deleted: server_sids.json")
        except Exception as e:
            print(f"   ❌ Error deleting server_sids.json: {e}")
    else:
        print("   ⚠️  server_sids.json not found")
    
    # 4. Delete list.json
    list_file = os.path.join(base_dir, "list.json")
    if os.path.exists(list_file):
        try:
            os.remove(list_file)
            print(f"   ✅ Deleted: list.json")
        except Exception as e:
            print(f"   ❌ Error deleting list.json: {e}")
    else:
        print("   ⚠️  list.json not found")
    
    print("\n✨ Clean up complete!")
    print("📊 daemon.json is now reset to [] and ready for new logs")

if __name__ == "__main__":
    clean()
