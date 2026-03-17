#!/usr/bin/env python3
import random
import time
from datetime import datetime
import os

os.makedirs("logs", exist_ok=True)

events = [
    "CPUUsageHigh",
    "MemoryUsageHigh",
    "DiskUsageWarning",
    "ServiceRestart",
    "NetworkLatency"
]

levels = ["INFO", "WARN", "ERROR"]

print("Infra Server started. Writing logs to logs/infra_server.log")

i = 0

while (i <= 5):
    try:
        timestamp = datetime.now().isoformat()
        level = random.choice(levels)
        event = random.choice(events)

        metadata = f"cpu={random.randint(50,95)}% memory={random.randint(40,90)}%"

        log = f"{timestamp} | {level} | {event} | {metadata}"

        with open("logs/infra_server.log", "a") as f:
            f.write(log + "\n")
            f.flush()

        i = i + 1

        time.sleep(random.uniform(0.5, 2))
    except Exception as e:
        print(f"Error in Infra server: {e}")
        time.sleep(1)
