# import subprocess
# import os
# import sys
# import signal
# import time
#
# processes = []
#
# def signal_handler(sig, frame):
#     print("\nStopping all processes...")
#     for p in processes:
#         p.terminate()
#     
#     # Give processes time to terminate
#     time.sleep(2)
#     
#     # Force kill if still running
#     for p in processes:
#         if p.poll() is None:
#             p.kill()
#     
#     print("All processes stopped.")
#     sys.exit(0)
#
# signal.signal(signal.SIGINT, signal_handler)
#
# # Create logs directory if it doesn't exist
# os.makedirs("logs", exist_ok=True)
#
# # Start daemon first
# print("Starting daemon...")
# daemon = subprocess.Popen([sys.executable, "daemon/daemon.py"])
# processes.append(daemon)
#
# # Give daemon time to start
# time.sleep(2)
#
# servers = [
#     "module2_generator/servers/healthcare_server.py",
#     "module2_generator/servers/linux_server.py",
#     "module2_generator/servers/windows_server.py",
#     "module2_generator/servers/zookeeper_server.py"
# ]
#
# # Start all servers
# print("Starting servers (each will generate logs)...")
# for server in servers:
#     print(f"Starting {server}")
#     p = subprocess.Popen([sys.executable, server])
#     processes.append(p)
#     time.sleep(1)  # Small delay between starting servers
#
# print("\n" + "="*50)
# print("All processes started. Each server will generate logs.")
# print("The daemon is silently converting logs to JSON in daemon/daemon.json")
# print("Press Ctrl+C to stop all processes.")
# print("="*50 + "\n")
#
# try:
#     # Wait for all server processes to complete
#     server_processes = processes[1:]  # Exclude daemon
#     for p in server_processes:
#         p.wait()
#     
#     print("\nAll servers have finished generating logs.")
#     print("Daemon is still running. Press Ctrl+C to stop the daemon.")
#     
#     # Keep daemon running until Ctrl+C
#     processes[0].wait()
#     
# except KeyboardInterrupt:
#     signal_handler(None, None)









# #!/usr/bin/env python3
# """
# Unified Runner - Creates and runs multiple server instances
# Simple version - just asks for counts
# """
#
# import os
# import sys
# import json
# import uuid
# import hashlib
# import base64
# from datetime import datetime
#
# LIST_FILE = "list.json"
#
# # Try to import tabulate, provide fallback if not available
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
#             val = input("🏥 Healthcare servers: ").strip()
#             counts['HEALTHCARE'] = int(val) if val else 0
#             break
#         except ValueError:
#             print("   Please enter a number (0 if none)")
#     
#     # Zookeeper
#     while True:
#         try:
#             val = input("🦓 Zookeeper servers: ").strip()
#             counts['ZOOKEEPER'] = int(val) if val else 0
#             break
#         except ValueError:
#             print("   Please enter a number (0 if none)")
#     
#     # Windows
#     while True:
#         try:
#             val = input("🪟 Windows servers: ").strip()
#             counts['WINDOWS'] = int(val) if val else 0
#             break
#         except ValueError:
#             print("   Please enter a number (0 if none)")
#     
#     # Linux
#     while True:
#         try:
#             val = input("🐧 Linux servers: ").strip()
#             counts['LINUX'] = int(val) if val else 0
#             break
#         except ValueError:
#             print("   Please enter a number (0 if none)")
#     
#     return counts
#
# def create_servers(counts):
#     """Create server instances based on counts"""
#     servers = []
#     
#     for server_type, count in counts.items():
#         for i in range(count):
#             instance_num = i + 1
#             sid = generate_sid(server_type, instance_num)
#             
#             servers.append({
#                 'sid': sid,
#                 'type': server_type,
#                 'instance': instance_num,
#                 'status': 'registered'
#             })
#             print(f"   ➕ Added {server_type} instance #{instance_num:03d}")
#     
#     return servers
#
# def show_servers_simple(servers):
#     """Simple table without tabulate"""
#     print("\n" + "="*80)
#     print("📋 REGISTERED SERVERS")
#     print("="*80)
#     print(f"{'SID':<30} {'Type':<12} {'Instance':<8} {'Status':<10}")
#     print("-"*60)
#     
#     for s in servers:
#         # Truncate SID for display
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
#     print("🚀 LOG INTELLIGENT SYSTEM - SERVER REGISTRATION")
#     print("="*80)
#     
#     while True:
#         print("\n" + "-"*40)
#         print("Options:")
#         print("   1. Create new server list")
#         print("   2. Show current servers")
#         print("   3. Clear all servers")
#         print("   4. Exit")
#         print("-"*40)
#         
#         choice = input("Enter choice (1-4): ").strip()
#         
#         if choice == '1':
#             # Clear existing list first
#             if os.path.exists(LIST_FILE):
#                 os.remove(LIST_FILE)
#                 print("🗑️ Cleared existing server list")
#             
#             # Get counts
#             counts = get_server_counts()
#             
#             # Check if any servers were added
#             if sum(counts.values()) == 0:
#                 print("\n⚠️  No servers added!")
#                 continue
#             
#             # Create servers
#             print("\n🔧 Creating servers...")
#             servers = create_servers(counts)
#             
#             # Save to file
#             save_list(servers)
#             
#             # Show the list
#             show_servers(servers)
#             
#         elif choice == '2':
#             servers = load_list()
#             show_servers(servers)
#             
#         elif choice == '3':
#             if os.path.exists(LIST_FILE):
#                 os.remove(LIST_FILE)
#                 print("\n🗑️ Cleared all server registrations!")
#             else:
#                 print("\n📭 No list file found.")
#                 
#         elif choice == '4':
#             print("\n👋 Goodbye!")
#             break
#             
#         else:
#             print("\n❌ Invalid choice. Please enter 1-4")
#
# if __name__ == "__main__":
#     main()





#!/usr/bin/env python3
"""
Unified Runner - Creates and runs multiple server instances
CONTINUOUS version - adds to existing list.json
"""

import os
import sys
import json
import uuid
import hashlib
import base64
from datetime import datetime

LIST_FILE = "list.json"

# Try to import tabulate, provide fallback if not available
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
            print(f"   ➕ Added {server_type} instance #{instance_num:03d} → {sid[:15]}...")
    
    return existing_servers + new_servers

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

def main():
    print("\n" + "="*80)
    print("🚀 LOG INTELLIGENT SYSTEM - CONTINUOUS SERVER REGISTRATION")
    print("="*80)
    
    while True:
        print("\n" + "-"*40)
        print("Options:")
        print("   1. ADD MORE servers to existing list")
        print("   2. Show current servers")
        print("   3. Clear ALL servers (start fresh)")
        print("   4. Exit")
        print("-"*40)
        
        choice = input("Enter choice (1-4): ").strip()
        
        if choice == '1':
            # Load existing servers
            existing_servers = load_list()
            
            if existing_servers:
                print(f"\n📋 Found {len(existing_servers)} existing servers. Adding more...")
                show_servers_simple(existing_servers[:3])  # Show first 3 as preview
                print("   ...")
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
                
        elif choice == '4':
            print("\n👋 Goodbye!")
            break
            
        else:
            print("\n❌ Invalid choice. Please enter 1-4")

if __name__ == "__main__":
    main()
