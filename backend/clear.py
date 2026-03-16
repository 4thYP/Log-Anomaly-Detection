import os
import json

# Log files to clear
log_files = [
    "logs/db_server.log",
    "logs/auth_server.log",
    "logs/api_server.log",
    "logs/healthcare_server.log",
    "logs/infra_server.log"
]

# Clear log files
for log in log_files:
    if os.path.exists(log):
        open(log, "w").close()

# Reset daemon.json
daemon_file = "daemon/daemon.json"

if os.path.exists(daemon_file):
    with open(daemon_file, "w") as f:
        json.dump([], f, indent=4)

print("Logs and daemon.json cleared.")
