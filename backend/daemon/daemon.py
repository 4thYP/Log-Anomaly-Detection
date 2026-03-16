#!/usr/bin/env python3

import os
import json
import time
import threading

LOG_DIR = "servers"
OUTPUT_FILE = "daemon.json"

lock = threading.Lock()


def parse_log(server_name, line):
    parts = [p.strip() for p in line.split("|")]

    if len(parts) < 3:
        return None

    timestamp = parts[0]
    level = parts[1]
    message = parts[2]

    return {
        "timestamp": timestamp,
        "level": level,
        "service": server_name.replace(".log", ""),
        "message": message
    }


def write_log(entry):
    with lock:

        if not os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, "w") as f:
                json.dump([], f)

        try:
            with open(OUTPUT_FILE, "r") as f:
                data = json.load(f)
        except:
            data = []

        data.append(entry)

        with open(OUTPUT_FILE, "w") as f:
            json.dump(data, f, indent=2)


def monitor_file(filepath):

    server_name = os.path.basename(filepath)

    print("Monitoring:", filepath)

    with open(filepath, "r") as f:

        f.seek(0, os.SEEK_END)

        while True:
            line = f.readline()

            if not line:
                time.sleep(0.2)
                continue

            parsed = parse_log(server_name, line.strip())

            if parsed:
                write_log(parsed)
                print("Processed:", parsed["service"], parsed["message"])


def start_daemon():

    print("Daemon started")

    for file in os.listdir(LOG_DIR):

        if file.endswith(".log"):

            filepath = os.path.join(LOG_DIR, file)

            t = threading.Thread(
                target=monitor_file,
                args=(filepath,),
                daemon=True
            )

            t.start()

    while True:
        time.sleep(5)


if __name__ == "__main__":
    start_daemon()
