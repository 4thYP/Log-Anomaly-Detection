#!/usr/bin/env python3
import random
import time
from datetime import datetime
import os

os.makedirs("logs", exist_ok=True)

events = [
    "LoginSuccess",
    "LoginFailure",
    "TokenGenerated",
    "PasswordReset",
    "UserLogout"
]

levels = ["INFO", "WARN", "ERROR"]

print("Auth Server started. Writing logs to logs/auth_server.log")

i = 0

while (i <= 5):
    try:
        timestamp = datetime.now().isoformat()
        level = random.choice(levels)
        event = random.choice(events)

        metadata = f"user_id={random.randint(100,999)} ip=192.168.1.{random.randint(1,255)}"

        log = f"{timestamp} | {level} | {event} | {metadata}"

        with open("logs/auth_server.log", "a") as f:
            f.write(log + "\n")
            f.flush()

        i = i + 1

        time.sleep(random.uniform(0.5, 2))
    except Exception as e:
        print(f"Error in Auth server: {e}")
        time.sleep(1)
