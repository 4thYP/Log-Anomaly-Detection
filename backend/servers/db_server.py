import random
import time
from datetime import datetime

events = [
    "QueryExecuted",
    "ConnectionOpened",
    "ConnectionClosed",
    "SlowQuery",
    "TransactionCommit"
]

levels = ["INFO", "WARN", "ERROR"]

for i in range(5):

    timestamp = datetime.now().isoformat()
    level = random.choice(levels)
    event = random.choice(events)

    metadata = f"query_time={random.randint(10,500)}ms"

    log = f"{timestamp} | {level} | {event} | {metadata}"

    with open("logs/db_server.log", "a") as f:
        f.write(log + "\n")

    time.sleep(1)