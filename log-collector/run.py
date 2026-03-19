# #!/usr/bin/env python3
# """
# Unified Runner - Creates and runs multiple server instances
# CONTINUOUS version with --run to start all servers
# """
#
# import os
# import sys
# import json
# import uuid
# import hashlib
# import base64
# import subprocess
# import time
# import signal
# from datetime import datetime
#
# LIST_FILE = "list.json"
# SERVER_SCRIPTS = {
#     'HEALTHCARE': 'module2_generator/servers/healthcare_server.py',
#     'LINUX': 'module2_generator/servers/linux_server.py',
#     'WINDOWS': 'module2_generator/servers/windows_server.py',
#     'ZOOKEEPER': 'module2_generator/servers/zookeeper_server.py'
# }
#
# # Global list to track running processes
# processes = []
#
# def signal_handler(sig, frame):
#     """Handle Ctrl+C to stop all servers"""
#     print("\n\n🛑 Stopping all servers...")
#     for p in processes:
#         p.terminate()
#     
#     time.sleep(2)
#     
#     for p in processes:
#         if p.poll() is None:
#             p.kill()
#     
#     print("✅ All servers stopped.")
#     sys.exit(0)
#
# signal.signal(signal.SIGINT, signal_handler)
#
# # Try to import tabulate
# try:
#     from tabulate import tabulate
#     HAS_TABULATE = True
# except ImportError:
#     HAS_TABULATE = False
#     print("⚠️  'tabulate' not installed. Run: pip install tabulate")
#     print("   Using simple table format instead.\n")
#
# def load_list():
#     """Load existing server list"""
#     if os.path.exists(LIST_FILE):
#         try:
#             with open(LIST_FILE, 'r') as f:
#                 return json.load(f)
#         except:
#             return []
#     return []
#
# def save_list(servers):
#     """Save server list to file"""
#     with open(LIST_FILE, 'w') as f:
#         json.dump(servers, f, indent=2)
#     print(f"\n💾 Saved {len(servers)} servers to {LIST_FILE}")
#
# def generate_sid(server_type, instance_num):
#     """Generate a unique SID for a server instance"""
#     unique_str = str(uuid.uuid4()) + str(instance_num) + str(datetime.now().timestamp())
#     hashed = hashlib.sha256(unique_str.encode()).digest()
#     random_str = base64.b64encode(hashed).decode('utf-8')[:20]
#     random_str = ''.join(c for c in random_str if c.isalnum())
#     return f"{random_str}_{server_type}_{instance_num:03d}"
#
# def get_highest_instance(servers, server_type):
#     """Find the highest instance number for a given server type"""
#     instances = [s['instance'] for s in servers if s['type'] == server_type]
#     return max(instances) if instances else 0
#
# def get_server_counts():
#     """Ask user for number of each server type"""
#     print("\n📊 Enter number of servers for each type:")
#     print("-" * 40)
#     
#     counts = {}
#     
#     # Healthcare
#     while True:
#         try:
#             val = input("🏥 Healthcare servers (to ADD): ").strip()
#             counts['HEALTHCARE'] = int(val) if val else 0
#             break
#         except ValueError:
#             print("   Please enter a number (0 if none)")
#     
#     # Zookeeper
#     while True:
#         try:
#             val = input("🦓 Zookeeper servers (to ADD): ").strip()
#             counts['ZOOKEEPER'] = int(val) if val else 0
#             break
#         except ValueError:
#             print("   Please enter a number (0 if none)")
#     
#     # Windows
#     while True:
#         try:
#             val = input("🪟 Windows servers (to ADD): ").strip()
#             counts['WINDOWS'] = int(val) if val else 0
#             break
#         except ValueError:
#             print("   Please enter a number (0 if none)")
#     
#     # Linux
#     while True:
#         try:
#             val = input("🐧 Linux servers (to ADD): ").strip()
#             counts['LINUX'] = int(val) if val else 0
#             break
#         except ValueError:
#             print("   Please enter a number (0 if none)")
#     
#     return counts
#
# def add_servers(existing_servers, counts):
#     """ADD new server instances to existing list"""
#     new_servers = []
#     
#     for server_type, count in counts.items():
#         if count == 0:
#             continue
#             
#         # Find highest existing instance for this type
#         start_num = get_highest_instance(existing_servers, server_type) + 1
#         
#         for i in range(count):
#             instance_num = start_num + i
#             sid = generate_sid(server_type, instance_num)
#             
#             new_server = {
#                 'sid': sid,
#                 'type': server_type,
#                 'instance': instance_num,
#                 'status': 'registered'
#             }
#             new_servers.append(new_server)
#             print(f"   ➕ Added {server_type} instance #{instance_num:03d}")
#     
#     return existing_servers + new_servers
#
# def run_servers(servers):
#     """Launch all servers as separate processes"""
#     if not servers:
#         print("\n❌ No servers to run! Add servers first (Option 1).")
#         return
#     
#     print("\n" + "="*80)
#     print(f"🚀 LAUNCHING {len(servers)} SERVERS")
#     print("="*80)
#     
#     # Group servers by type
#     server_groups = {}
#     for server in servers:
#         s_type = server['type']
#         if s_type not in server_groups:
#             server_groups[s_type] = []
#         server_groups[s_type].append(server)
#     
#     # Start daemon first
#     print("\n🔄 Starting daemon...")
#     daemon = subprocess.Popen([sys.executable, "daemon/daemon.py"])
#     processes.append(daemon)
#     print("   ✅ Daemon started")
#     time.sleep(2)
#     
#     # Start servers by type
#     for server_type, server_list in server_groups.items():
#         script_path = SERVER_SCRIPTS.get(server_type)
#         if not script_path or not os.path.exists(script_path):
#             print(f"   ❌ Script not found for {server_type}: {script_path}")
#             continue
#         
#         print(f"\n📂 Starting {len(server_list)} {server_type} servers...")
#         
#         for server in server_list:
#             # Set environment variable for this server instance
#             env = os.environ.copy()
#             env['SERVER_SID'] = server['sid']
#             env['SERVER_TYPE'] = server['type']
#             env['SERVER_INSTANCE'] = str(server['instance'])
#             
#             # Launch server process
#             p = subprocess.Popen(
#                 [sys.executable, script_path],
#                 env=env
#             )
#             processes.append(p)
#             print(f"   ✅ {server['type']} #{server['instance']:03d} started (SID: {server['sid'][:15]}...)")
#             time.sleep(0.5)  # Small delay between servers
#     
#     print("\n" + "="*80)
#     print(f"✅ ALL {len(servers)} SERVERS ARE RUNNING!")
#     print("📝 Logs are being written to:")
#     print("   • logs/*.log (raw logs)")
#     print("   • daemon/daemon.json (structured for ML)")
#     print("\n🛑 Press Ctrl+C to stop all servers")
#     print("="*80)
#
# def show_servers_simple(servers):
#     """Simple table without tabulate"""
#     if not servers:
#         print("\n📋 No servers registered yet.")
#         return
#         
#     print("\n" + "="*80)
#     print("📋 REGISTERED SERVERS")
#     print("="*80)
#     print(f"{'SID':<30} {'Type':<12} {'Instance':<8} {'Status':<10}")
#     print("-"*60)
#     
#     for s in servers:
#         short_sid = s['sid'][:25] + "..." if len(s['sid']) > 25 else s['sid']
#         print(f"{short_sid:<30} {s['type']:<12} #{s['instance']:03d}      {s['status']:<10}")
#     
#     print("="*80)
#     print(f"📊 Total: {len(servers)} servers")
#
# def show_servers(servers):
#     """Display servers in a table"""
#     if not servers:
#         print("\n📋 No servers registered yet.")
#         return
#     
#     if HAS_TABULATE:
#         table_data = []
#         for s in servers:
#             table_data.append([
#                 s['sid'][:15] + "...",
#                 s['type'],
#                 f"#{s['instance']:03d}",
#                 s['status']
#             ])
#         
#         print("\n" + "="*80)
#         print("📋 REGISTERED SERVERS")
#         print("="*80)
#         print(tabulate(table_data, 
#                       headers=['SID (truncated)', 'Type', 'Instance', 'Status'],
#                       tablefmt='grid'))
#         print(f"\n📊 Total: {len(servers)} servers")
#     else:
#         show_servers_simple(servers)
#
# def main():
#     print("\n" + "="*80)
#     print("🚀 LOG INTELLIGENT SYSTEM - SERVER MANAGER")
#     print("="*80)
#     
#     while True:
#         print("\n" + "-"*40)
#         print("Options:")
#         print("   1. ADD MORE servers to list")
#         print("   2. Show current servers")
#         print("   3. Clear ALL servers (start fresh)")
#         print("   4. --RUN all servers (start generating logs)")
#         print("   5. Exit")
#         print("-"*40)
#         
#         choice = input("Enter choice (1-5): ").strip()
#         
#         if choice == '1':
#             # Load existing servers
#             existing_servers = load_list()
#             
#             if existing_servers:
#                 print(f"\n📋 Found {len(existing_servers)} existing servers. Adding more...")
#             else:
#                 print("\n📭 No existing servers. Creating new list...")
#             
#             # Get counts to ADD
#             counts = get_server_counts()
#             
#             # Check if any servers were added
#             if sum(counts.values()) == 0:
#                 print("\n⚠️  No servers added!")
#                 continue
#             
#             # ADD new servers to existing list
#             print("\n🔧 Adding servers...")
#             updated_servers = add_servers(existing_servers, counts)
#             
#             # Update status
#             for server in updated_servers:
#                 server['status'] = 'registered'
#             
#             # Save to file
#             save_list(updated_servers)
#             
#             # Show the updated list
#             show_servers(updated_servers)
#             
#         elif choice == '2':
#             servers = load_list()
#             show_servers(servers)
#             
#         elif choice == '3':
#             if os.path.exists(LIST_FILE):
#                 os.remove(LIST_FILE)
#                 print("\n🗑️ Cleared ALL server registrations! Starting fresh.")
#             else:
#                 print("\n📭 No list file found.")
#         
#         elif choice == '4' or choice == '--run':
#             servers = load_list()
#             if servers:
#                 # Update status to running
#                 for server in servers:
#                     server['status'] = 'running'
#                 save_list(servers)
#                 
#                 # Show what's about to run
#                 show_servers(servers)
#                 
#                 # Run them!
#                 run_servers(servers)
#                 
#                 # Keep the program running to monitor
#                 try:
#                     while True:
#                         time.sleep(1)
#                 except KeyboardInterrupt:
#                     signal_handler(None, None)
#             else:
#                 print("\n❌ No servers to run! Add servers first (Option 1).")
#                 
#         elif choice == '5':
#             print("\n👋 Goodbye!")
#             break
#             
#         else:
#             print("\n❌ Invalid choice. Please enter 1-5")
#
# if __name__ == "__main__":
#     main()

#!/usr/bin/env python3
"""
Unified Runner - Creates and runs multiple server instances
CONTINUOUS version with --run to start all servers
"""

import os
import sys
import json
import uuid
import hashlib
import base64
import subprocess
import time
import signal
from datetime import datetime

LIST_FILE = "list.json"
SERVER_SCRIPTS = {
    'HEALTHCARE': 'module2_generator/servers/healthcare_server.py',
    'LINUX': 'module2_generator/servers/linux_server.py',
    'WINDOWS': 'module2_generator/servers/windows_server.py',
    'ZOOKEEPER': 'module2_generator/servers/zookeeper_server.py'
}

# Global list to track running processes
processes = []

def signal_handler(sig, frame):
    """Handle Ctrl+C to stop all servers"""
    print("\n\n🛑 Stopping all servers...")
    for p in processes:
        p.terminate()
    
    time.sleep(2)
    
    for p in processes:
        if p.poll() is None:
            p.kill()
    
    print("✅ All servers stopped.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Try to import tabulate
try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False
    print("⚠️  'tabulate' not installed. Run: pip install tabulate")
    print("   Using simple table format instead.\n")

def load_list():
    """Load existing server list"""
    if os.path.exists(LIST_FILE):
        try:
            with open(LIST_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_list(servers):
    """Save server list to file"""
    with open(LIST_FILE, 'w') as f:
        json.dump(servers, f, indent=2)
    print(f"\n💾 Saved {len(servers)} servers to {LIST_FILE}")

def generate_sid(server_type, instance_num):
    """Generate a unique SID for a server instance"""
    unique_str = str(uuid.uuid4()) + str(instance_num) + str(datetime.now().timestamp())
    hashed = hashlib.sha256(unique_str.encode()).digest()
    random_str = base64.b64encode(hashed).decode('utf-8')[:20]
    random_str = ''.join(c for c in random_str if c.isalnum())
    return f"{random_str}_{server_type}_{instance_num:03d}"

def get_highest_instance(servers, server_type):
    """Find the highest instance number for a given server type"""
    instances = [s['instance'] for s in servers if s['type'] == server_type]
    return max(instances) if instances else 0

def get_server_counts():
    """Ask user for number of each server type"""
    print("\n📊 Enter number of servers for each type:")
    print("-" * 40)
    
    counts = {}
    
    # Healthcare
    while True:
        try:
            val = input("🏥 Healthcare servers (to ADD): ").strip()
            counts['HEALTHCARE'] = int(val) if val else 0
            break
        except ValueError:
            print("   Please enter a number (0 if none)")
    
    # Zookeeper
    while True:
        try:
            val = input("🦓 Zookeeper servers (to ADD): ").strip()
            counts['ZOOKEEPER'] = int(val) if val else 0
            break
        except ValueError:
            print("   Please enter a number (0 if none)")
    
    # Windows
    while True:
        try:
            val = input("🪟 Windows servers (to ADD): ").strip()
            counts['WINDOWS'] = int(val) if val else 0
            break
        except ValueError:
            print("   Please enter a number (0 if none)")
    
    # Linux
    while True:
        try:
            val = input("🐧 Linux servers (to ADD): ").strip()
            counts['LINUX'] = int(val) if val else 0
            break
        except ValueError:
            print("   Please enter a number (0 if none)")
    
    return counts

def add_servers(existing_servers, counts):
    """ADD new server instances to existing list"""
    new_servers = []
    
    for server_type, count in counts.items():
        if count == 0:
            continue
            
        # Find highest existing instance for this type
        start_num = get_highest_instance(existing_servers, server_type) + 1
        
        for i in range(count):
            instance_num = start_num + i
            sid = generate_sid(server_type, instance_num)
            
            new_server = {
                'sid': sid,
                'type': server_type,
                'instance': instance_num,
                'status': 'registered'
            }
            new_servers.append(new_server)
            print(f"   ➕ Added {server_type} instance #{instance_num:03d}")
    
    return existing_servers + new_servers

def run_servers(servers):
    """Launch all servers as separate processes"""
    if not servers:
        print("\n❌ No servers to run! Add servers first (Option 1).")
        return
    
    print("\n" + "="*80)
    print(f"🚀 LAUNCHING {len(servers)} SERVERS")
    print("="*80)
    
    # Group servers by type
    server_groups = {}
    for server in servers:
        s_type = server['type']
        if s_type not in server_groups:
            server_groups[s_type] = []
        server_groups[s_type].append(server)
    
    # Start daemon first
    print("\n🔄 Starting daemon...")
    daemon = subprocess.Popen([sys.executable, "daemon/daemon.py"])
    processes.append(daemon)
    print("   ✅ Daemon started")
    time.sleep(2)
    
    # Start servers by type
    for server_type, server_list in server_groups.items():
        script_path = SERVER_SCRIPTS.get(server_type)
        if not script_path or not os.path.exists(script_path):
            print(f"   ❌ Script not found for {server_type}: {script_path}")
            continue
        
        print(f"\n📂 Starting {len(server_list)} {server_type} servers...")
        
        for server in server_list:
            # Set environment variables for this server instance
            env = os.environ.copy()
            env['SERVER_SID'] = server['sid']
            env['SERVER_TYPE'] = server['type']
            env['SERVER_INSTANCE'] = str(server['instance'])
            
            # Launch server process
            p = subprocess.Popen(
                [sys.executable, script_path],
                env=env
            )
            processes.append(p)
            print(f"   ✅ {server['type']} #{server['instance']:03d} started (SID: {server['sid'][:15]}...)")
            time.sleep(0.5)  # Small delay between servers
    
    print("\n" + "="*80)
    print(f"✅ ALL {len(servers)} SERVERS ARE RUNNING!")
    print("📝 Logs are being written to:")
    print("   • logs/*_*.log (one file per server instance)")
    print("   • daemon/daemon.json (structured for ML)")
    print("\n🛑 Press Ctrl+C to stop all servers")
    print("="*80)

def show_servers_simple(servers):
    """Simple table without tabulate"""
    if not servers:
        print("\n📋 No servers registered yet.")
        return
        
    print("\n" + "="*80)
    print("📋 REGISTERED SERVERS")
    print("="*80)
    print(f"{'SID':<30} {'Type':<12} {'Instance':<8} {'Status':<10}")
    print("-"*60)
    
    for s in servers:
        short_sid = s['sid'][:25] + "..." if len(s['sid']) > 25 else s['sid']
        print(f"{short_sid:<30} {s['type']:<12} #{s['instance']:03d}      {s['status']:<10}")
    
    print("="*80)
    print(f"📊 Total: {len(servers)} servers")

def show_servers(servers):
    """Display servers in a table"""
    if not servers:
        print("\n📋 No servers registered yet.")
        return
    
    if HAS_TABULATE:
        table_data = []
        for s in servers:
            table_data.append([
                s['sid'][:15] + "...",
                s['type'],
                f"#{s['instance']:03d}",
                s['status']
            ])
        
        print("\n" + "="*80)
        print("📋 REGISTERED SERVERS")
        print("="*80)
        print(tabulate(table_data, 
                      headers=['SID (truncated)', 'Type', 'Instance', 'Status'],
                      tablefmt='grid'))
        print(f"\n📊 Total: {len(servers)} servers")
    else:
        show_servers_simple(servers)

def clear_logs_folder():
    """Delete ALL log files in logs folder before starting servers"""
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    if os.path.exists(logs_dir):
        log_files = glob.glob(os.path.join(logs_dir, "*.log"))
        for log_file in log_files:
            try:
                os.remove(log_file)
                print(f"   🗑️ Deleted old log: {os.path.basename(log_file)}")
            except Exception as e:
                print(f"   ❌ Error deleting {log_file}: {e}")

def reset_daemon_json():
    """Reset daemon.json to empty array []"""
    daemon_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daemon", "daemon.json")
    os.makedirs(os.path.dirname(daemon_json), exist_ok=True)
    try:
        with open(daemon_json, 'w') as f:
            json.dump([], f, indent=2)
        print("   🗑️ Reset daemon.json to []")
    except Exception as e:
        print(f"   ❌ Error resetting daemon.json: {e}")

def main():
    print("\n" + "="*80)
    print("🚀 LOG INTELLIGENT SYSTEM - SERVER MANAGER")
    print("="*80)
    
    while True:
        print("\n" + "-"*40)
        print("Options:")
        print("   1. ADD MORE servers to list")
        print("   2. Show current servers")
        print("   3. Clear ALL servers (start fresh)")
        print("   4. --RUN all servers (start generating logs)")
        print("   5. Exit")
        print("-"*40)
        
        choice = input("Enter choice (1-5): ").strip()
        
        if choice == '1':
            # Load existing servers
            existing_servers = load_list()
            
            if existing_servers:
                print(f"\n📋 Found {len(existing_servers)} existing servers. Adding more...")
            else:
                print("\n📭 No existing servers. Creating new list...")
            
            # Get counts to ADD
            counts = get_server_counts()
            
            # Check if any servers were added
            if sum(counts.values()) == 0:
                print("\n⚠️  No servers added!")
                continue
            
            # ADD new servers to existing list
            print("\n🔧 Adding servers...")
            updated_servers = add_servers(existing_servers, counts)
            
            # Update status
            for server in updated_servers:
                server['status'] = 'registered'
            
            # Save to file
            save_list(updated_servers)
            
            # Show the updated list
            show_servers(updated_servers)
            
        elif choice == '2':
            servers = load_list()
            show_servers(servers)
            
        elif choice == '3':
            if os.path.exists(LIST_FILE):
                os.remove(LIST_FILE)
                print("\n🗑️ Cleared ALL server registrations! Starting fresh.")
            else:
                print("\n📭 No list file found.")
        
        elif choice == '4' or choice == '--run':
            servers = load_list()
            if servers:
                # IMPORTANT: Clean up old logs before starting new run
                print("\n🧹 Preparing for fresh run...")
                clear_logs_folder()
                reset_daemon_json()
                
                # Update status to running
                for server in servers:
                    server['status'] = 'running'
                save_list(servers)
                
                # Show what's about to run
                show_servers(servers)
                
                # Run them!
                run_servers(servers)
                
                # Keep the program running to monitor
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    signal_handler(None, None)
            else:
                print("\n❌ No servers to run! Add servers first (Option 1).")
                
        elif choice == '5':
            print("\n👋 Goodbye!")
            break
            
        else:
            print("\n❌ Invalid choice. Please enter 1-5")

if __name__ == "__main__":
    # Add glob import at the top of the function where it's used
    import glob
    main()
