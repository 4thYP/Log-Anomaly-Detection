# #!/usr/bin/env python3
# """
# Clean up script - resets all generated files
# Run this between tests to start fresh
# """
#
# import os
# import glob
# import json
#
# def clean():
#     print("🧹 Cleaning up generated files...")
#     
#     # Get the base directory
#     base_dir = os.path.dirname(os.path.abspath(__file__))
#     
#     # 1. Delete all .log files in logs directory
#     logs_dir = os.path.join(base_dir, "logs")
#     if os.path.exists(logs_dir):
#         log_files = glob.glob(os.path.join(logs_dir, "*.log"))
#         for log_file in log_files:
#             try:
#                 os.remove(log_file)
#                 print(f"   ✅ Deleted: logs/{os.path.basename(log_file)}")
#             except Exception as e:
#                 print(f"   ❌ Error deleting {log_file}: {e}")
#     else:
#         print("   ⚠️  logs directory not found")
#     
#     # 2. RESET daemon.json to [] (instead of deleting)
#     daemon_json = os.path.join(base_dir, "daemon", "daemon.json")
#     if os.path.exists(daemon_json):
#         try:
#             with open(daemon_json, 'w') as f:
#                 json.dump([], f, indent=2)
#             print(f"   ✅ Reset daemon/daemon.json to []")
#         except Exception as e:
#             print(f"   ❌ Error resetting daemon.json: {e}")
#     else:
#         # Create directory if it doesn't exist
#         os.makedirs(os.path.join(base_dir, "daemon"), exist_ok=True)
#         with open(daemon_json, 'w') as f:
#             json.dump([], f, indent=2)
#         print(f"   ✅ Created daemon/daemon.json with []")
#     
#     # 3. Delete server_sids.json
#     sid_file = os.path.join(base_dir, "server_sids.json")
#     if os.path.exists(sid_file):
#         try:
#             os.remove(sid_file)
#             print(f"   ✅ Deleted: server_sids.json")
#         except Exception as e:
#             print(f"   ❌ Error deleting server_sids.json: {e}")
#     else:
#         print("   ⚠️  server_sids.json not found")
#     
#     # 4. Delete list.json
#     list_file = os.path.join(base_dir, "list.json")
#     if os.path.exists(list_file):
#         try:
#             os.remove(list_file)
#             print(f"   ✅ Deleted: list.json")
#         except Exception as e:
#             print(f"   ❌ Error deleting list.json: {e}")
#     else:
#         print("   ⚠️  list.json not found")
#     
#     print("\n✨ Clean up complete!")
#     print("📊 daemon.json is now reset to [] and ready for new logs")
#
# if __name__ == "__main__":
#     clean()





#!/usr/bin/env python3
"""
Clean up script - deletes ALL generated files for a fresh start
"""

import os
import glob
import json
import re

def clean():
    print("🧹 Cleaning up ALL generated files...")
    
    # Get the base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Delete ALL .log files in logs directory (including instance files)
    logs_dir = os.path.join(base_dir, "logs")
    if os.path.exists(logs_dir):
        log_files = glob.glob(os.path.join(logs_dir, "*.log"))
        # Also look for pattern like healthcare_1.log, healthcare_2.log
        instance_logs = glob.glob(os.path.join(logs_dir, "*_*.log"))
        all_logs = set(log_files + instance_logs)
        
        for log_file in all_logs:
            try:
                os.remove(log_file)
                print(f"   ✅ Deleted: logs/{os.path.basename(log_file)}")
            except Exception as e:
                print(f"   ❌ Error deleting {log_file}: {e}")
    else:
        print("   ⚠️  logs directory not found")
    
    # 2. RESET daemon.json to [] (empty array)
    daemon_json = os.path.join(base_dir, "daemon", "daemon.json")
    os.makedirs(os.path.join(base_dir, "daemon"), exist_ok=True)
    try:
        with open(daemon_json, 'w') as f:
            json.dump([], f, indent=2)
        print(f"   ✅ Reset daemon/daemon.json to []")
    except Exception as e:
        print(f"   ❌ Error resetting daemon.json: {e}")
    
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
    print("📁 Logs folder is empty")
    print("📊 daemon.json is reset to []")
    print("🚀 Ready for fresh start!")

if __name__ == "__main__":
    clean()
