#!/usr/bin/env python3
import random
import time
from datetime import datetime
import os

os.makedirs("logs", exist_ok=True)

events = [
    "MRIProcessingStarted",
    "MRIProcessingTimeout",
    "PredictionRequested",
    "PatientRecordAccess",
    "ModelInference"
]

levels = ["INFO", "WARN", "ERROR"]

print("Healthcare Server started. Writing logs to logs/healthcare_server.log")

i = 0

while (i <= 5):
    try:
        timestamp = datetime.now().isoformat()
        level = random.choice(levels)
        event = random.choice(events)

        metadata = f"patient_id={random.randint(1000,9999)} latency={random.randint(100,5000)}ms"

        log = f"{timestamp} | {level} | {event} | {metadata}"

        with open("logs/healthcare_server.log", "a") as f:
            f.write(log + "\n")
            f.flush()

        i = i + 1

        time.sleep(random.uniform(0.5, 2))
    except Exception as e:
        print(f"Error in Healthcare server: {e}")
        time.sleep(1)
