# """Basic connection example.
# """
# # from redis import asyncio 
# import redis
#
# r = redis.Redis(
#     host='redis-16124.crce281.ap-south-1-3.ec2.cloud.redislabs.com',
#     port=16124,
#     decode_responses=True,
#     username="default",
#     password="136AMdYr8UIzzA0o5n2qQZIjFgBpyGb9",
# )
#
# success = r.set('foo', 'baer')
# # True
#
# result = r.get('foo')
# print(result)
# # >>> bar

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
load_dotenv()

# Read values from environment
redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_user = os.getenv("REDIS_USERNAME")
redis_pass = os.getenv("REDIS_PASSWORD")
redis_db = os.getenv("REDIS_DB")

# Connect with credentials
r = redis.Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True,
    username=redis_user,
    password=redis_pass,
    db=redis_db
)

KEY = "lis-logs"

# Blocking tail
while True:
    key, raw = r.brpop(KEY, timeout=0)  # blocks forever until a new log arrives
    log = json.loads(raw)
    print(log)
