#!/usr/bin/env python3
import random
import time
from datetime import datetime
import os

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

events = [
    "APIRequest",
    "EndpointHit",
    "Timeout",
    "InternalError",
    "ResponseSent"
]

levels = ["INFO", "WARN", "ERROR"]

print("API Server started. Writing logs to logs/api_server.log")

i = 0

while (i <= 5):  # Continuous loop instead of range(5)
    try:
        timestamp = datetime.now().isoformat()
        level = random.choice(levels)
        event = random.choice(events)

        metadata = f"endpoint=/predict status={random.choice([200,400,500])} latency={random.randint(50,1000)}ms"

        log = f"{timestamp} | {level} | {event} | {metadata}"

        with open("logs/api_server.log", "a") as f:
            f.write(log + "\n")
            f.flush()  # Ensure it's written immediately

        
        i = i + 1

        time.sleep(random.uniform(0.5, 2))  # Random delay between 0.5-2 seconds
    except Exception as e:
        print(f"Error in API server: {e}")
        time.sleep(1)
