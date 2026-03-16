import subprocess

processes = []

daemon = subprocess.Popen(["python3", "daemon/daemon.py"])
processes.append(daemon)

servers = [
    "servers/db_server.py",
    "servers/api_server.py",
    "servers/auth_server.py",
    "servers/infra_server.py",
    "servers/healthcare_server.py"
]

# Start all servers
for server in servers:
    p = subprocess.Popen(["python", server])
    processes.append(p)

try:
    for p in processes:
        p.wait()
except KeyboardInterrupt:
    print("Stopping all processes...")
    for p in processes:
        p.terminate()
