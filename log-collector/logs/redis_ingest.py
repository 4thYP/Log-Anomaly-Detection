from flask import Flask, request
import redis, json
from dotenv import load_dotenv
import os

app = Flask(__name__)

if os.path.exists('.env'):
    load_dotenv()

# Read values from environment
redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
redis_port = os.getenv("REDIS_PORT", 6379)
redis_user = os.getenv("REDIS_USERNAME", "myuser")
redis_pass = os.getenv("REDIS_PASSWORD", "mypassword")
redis_db = os.getenv("REDIS_DB", 0)

# Connect with credentials
r = redis.Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True,
    username=redis_user if redis_user else None,
    password=redis_pass if redis_pass else None,
    db=redis_db
)

@app.post("/ingest")
def ingest():
    log = request.get_json()
    r.rpush("lis-logs", json.dumps(log))  # push log into Redis list
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(port=5000)
