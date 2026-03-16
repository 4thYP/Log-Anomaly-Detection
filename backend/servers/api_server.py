import random
import time
from datetime import datetime

events = [
    "APIRequest",
    "EndpointHit",
    "Timeout",
    "InternalError",
    "ResponseSent"
]

levels = ["INFO", "WARN", "ERROR"]

for i in range(5):

    timestamp = datetime.now().isoformat()
    level = random.choice(levels)
    event = random.choice(events)

    metadata = f"endpoint=/predict status={random.choice([200,400,500])} latency={random.randint(50,1000)}ms"

    log = f"{timestamp} | {level} | {event} | {metadata}"

    with open("logs/api_server.log", "a") as f:
        f.write(log + "\n")

    time.sleep(1)