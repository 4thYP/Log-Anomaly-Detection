#!/usr/bin/env python3
import random
import time
from datetime import datetime
import os

os.makedirs("logs", exist_ok=True)

events = [
    "QueryExecuted",
    "ConnectionOpened",
    "ConnectionClosed",
    "SlowQuery",
    "TransactionCommit"
]

levels = ["INFO", "WARN", "ERROR"]

print("DB Server started. Writing logs to logs/db_server.log")

i = 0

while (i <= 5):
    try:
        timestamp = datetime.now().isoformat()
        level = random.choice(levels)
        event = random.choice(events)

        metadata = f"query_time={random.randint(10,500)}ms rows={random.randint(1,1000)}"

        log = f"{timestamp} | {level} | {event} | {metadata}"

        with open("logs/db_server.log", "a") as f:
            f.write(log + "\n")
            f.flush()

        i = i + 1

        time.sleep(random.uniform(0.5, 2))
    except Exception as e:
        print(f"Error in DB server: {e}")
        time.sleep(1)
