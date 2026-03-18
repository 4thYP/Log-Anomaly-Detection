import subprocess
import os
import sys
import signal
import time

processes = []

def signal_handler(sig, frame):
    print("\nStopping all processes...")
    for p in processes:
        p.terminate()
    
    # Give processes time to terminate
    time.sleep(2)
    
    # Force kill if still running
    for p in processes:
        if p.poll() is None:
            p.kill()
    
    print("All processes stopped.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Start daemon first
print("Starting daemon...")
daemon = subprocess.Popen([sys.executable, "daemon/daemon.py"])
processes.append(daemon)

# Give daemon time to start
time.sleep(2)

servers = [
    "module2_generator/servers/healthcare_server.py",
    "module2_generator/servers/linux_server.py",
    "module2_generator/servers/windows_server.py",
    "module2_generator/servers/zookeeper_server.py"
]

# Start all servers
print("Starting servers (each will generate logs)...")
for server in servers:
    print(f"Starting {server}")
    p = subprocess.Popen([sys.executable, server])
    processes.append(p)
    time.sleep(1)  # Small delay between starting servers

print("\n" + "="*50)
print("All processes started. Each server will generate logs.")
print("The daemon is silently converting logs to JSON in daemon/daemon.json")
print("Press Ctrl+C to stop all processes.")
print("="*50 + "\n")

try:
    # Wait for all server processes to complete
    server_processes = processes[1:]  # Exclude daemon
    for p in server_processes:
        p.wait()
    
    print("\nAll servers have finished generating logs.")
    print("Daemon is still running. Press Ctrl+C to stop the daemon.")
    
    # Keep daemon running until Ctrl+C
    processes[0].wait()
    
except KeyboardInterrupt:
    signal_handler(None, None)
