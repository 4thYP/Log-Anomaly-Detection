import random
import time
from datetime import datetime

events = [
    "LoginSuccess",
    "LoginFailure",
    "TokenGenerated",
    "PasswordReset",
    "UserLogout"
]

levels = ["INFO", "WARN", "ERROR"]

for i in range(5):

    timestamp = datetime.now().isoformat()
    level = random.choice(levels)
    event = random.choice(events)

    metadata = f"user_id={random.randint(100,999)} ip=192.168.1.{random.randint(1,255)}"

    log = f"{timestamp} | {level} | {event} | {metadata}"

    with open("logs/auth_server.log", "a") as f:
        f.write(log + "\n")

    time.sleep(1)