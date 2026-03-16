import random
import time
from datetime import datetime

events = [
    "CPUUsageHigh",
    "MemoryUsageHigh",
    "DiskUsageWarning",
    "ServiceRestart",
    "NetworkLatency"
]

levels = ["INFO", "WARN", "ERROR"]

for i in range(5):

    timestamp = datetime.now().isoformat()
    level = random.choice(levels)
    event = random.choice(events)

    metadata = f"cpu={random.randint(50,95)}%"

    log = f"{timestamp} | {level} | {event} | {metadata}"

    with open("logs/infra_server.log", "a") as f:
        f.write(log + "\n")

    time.sleep(1)