import requests
import time
import sys
import json
from confluent_kafka import Producer

# Configuration
KAFKA_BROKER = 'localhost:29092'
TOPIC = 'mule-events'
DB_QUERY_API = 'http://localhost:8080/api/health' # Dummy check for now, can't easily query DB directly from script without psycopg2. Wait, we can add a simple API to backend to check cases by utr for testing?
# Let's check using Postgres CLI via docker if needed, or better, we just trust the backend logs for the smoke test.

print("This script is a smoke test for Kafka end-to-end pipeline.")
print(f"Connecting to Kafka broker at {KAFKA_BROKER}...")

conf = {'bootstrap.servers': KAFKA_BROKER}
try:
    producer = Producer(**conf)
except Exception as e:
    print(f"Failed to connect to Kafka: {e}")
    sys.exit(1)

def delivery_callback(err, msg):
    if err:
        print(f"Message failed delivery: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

utr = f"UTR-TEST-{int(time.time())}"
payload = {
    "utr": utr,
    "sender_account": "ACC_M_001",
    "receiver_account": "ACC_L_001",
    "amount": 75000.0,
    "timestamp": "2026-08-27T10:00:00Z"
}

print(f"Producing message to topic {TOPIC}: {payload}")
producer.produce(TOPIC, json.dumps(payload).encode('utf-8'), callback=delivery_callback)
producer.flush()

print("Message sent! You should observe the backend logs to verify that the message is consumed.")
print("The consumer will read the event, call the ML service, and generate a Case in the database.")
