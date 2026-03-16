import random
import time
from datetime import datetime

events = [
    "MRIProcessingStarted",
    "MRIProcessingTimeout",
    "PredictionRequested",
    "PatientRecordAccess",
    "ModelInference"
]

levels = ["INFO", "WARN", "ERROR"]

for i in range(5):

    timestamp = datetime.now().isoformat()
    level = random.choice(levels)
    event = random.choice(events)

    metadata = f"patient_id={random.randint(1000,9999)} latency={random.randint(100,5000)}ms"

    log = f"{timestamp} | {level} | {event} | {metadata}"

    with open("logs/healthcare_server.log", "a") as f:
        f.write(log + "\n")

    time.sleep(1)
