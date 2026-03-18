"""Basic connection example.
"""
 
import redis
 
r = redis.Redis(
    host='redis-16124.crce281.ap-south-1-3.ec2.cloud.redislabs.com',
    port=16124,
    decode_responses=True,
    username="default",
    password="136AMdYr8UIzzA0o5n2qQZIjFgBpyGb9",
)
 
success = r.set('test1', 'bar')
# True
 
result = r.get('khanki')
print(result)
# >>> bar
