import redis
import mysql.connector

# Redis setup
redis_client = redis.StrictRedis(host="localhost", port=6379, decode_responses=True)

# MySQL setup
db_connection = mysql.connector.connect(
    host="localhost",
    user="your_username",
    password="your_password",
    database="pebble"
)
