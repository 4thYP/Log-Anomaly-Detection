from flask import Flask, request
import redis, json

app = Flask(__name__)

r = redis.Redis(
    host='redis-16124.crce281.ap-south-1-3.ec2.cloud.redislabs.com',
    port=16124,
    username="default",
    password="136AMdYr8UIzzA0o5n2qQZIjFgBpyGb9",
    decode_responses=True,
    db=0
)

@app.post("/ingest")
def ingest():
    log = request.get_json()
    r.rpush("lis-logs", json.dumps(log))  # push log into Redis list
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(port=5000)
