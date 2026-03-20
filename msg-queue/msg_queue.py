import json
import redis
from dotenv import load_dotenv
import os

# -----------------------
# HARD‑CODED CREDENTIALS
# -----------------------
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_USER = "myuser"
REDIS_PASSWORD = "mypassword"
REDIS_DB = 0

# Load .env file
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

KEY = "lis-logs"

# Blocking tail
while True:
    key, raw = r.brpop(KEY, timeout=0)  # blocks forever until a new log arrives
    log = json.loads(raw)
    print(log)
