import json
import os
import time
from datetime import datetime
import requests
from confluent_kafka import Consumer, KafkaError
import redis

# Configuration
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
BACKEND_URL = os.getenv("BACKEND_API_URL", "http://localhost:8080")
ML_URL = "http://localhost:8000"  # Self ML service url

print(f"[Streaming] Initializing Kafka consumer on {KAFKA_BOOTSTRAP}")
print(f"[Streaming] Initializing Redis connection on {REDIS_HOST}:{REDIS_PORT}")

# Connect to Redis
try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    r.ping()
    print("[Streaming] Connected to Redis successfully.")
except Exception as e:
    print(f"[Streaming] Redis connection failed: {e}")
    r = None

# Connect to Kafka Consumer
conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP,
    'group.id': 'mulenet-stream-processor',
    'auto.offset.reset': 'latest'
}

consumer = None
try:
    consumer = Consumer(conf)
    consumer.subscribe(['upi.transactions'])
    print("[Streaming] Subscribed to Kafka topic 'upi.transactions'")
except Exception as e:
    print(f"[Streaming] Kafka consumer setup failed: {e}. Running in standby.")


def parse_time(ts_str):
    try:
        s = ts_str.replace('Z', '')
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return time.time()


def update_redis_windows(txn):
    if not r:
        return {}

    sender = txn.get("sender_account")
    receiver = txn.get("receiver_account")
    amount = float(txn.get("amount", 0.0))
    ts = parse_time(txn.get("timestamp"))
    utr = txn.get("utr")

    now = time.time()

    # 1. Update Sender's outgoing activity (for 5 min count and 60 min outflow)
    sender_sent_key = f"txn:{sender}:sent"
    r.zadd(sender_sent_key, {f"{utr}:{amount}": ts})
    # Evict records older than 1 hour (3600 seconds)
    r.zremrangebyscore(sender_sent_key, 0, now - 3600)

    # 2. Update Receiver's incoming activity (for 30 min inflow and 60 min inflow)
    receiver_recv_key = f"txn:{receiver}:recv"
    r.zadd(receiver_recv_key, {f"{utr}:{amount}": ts})
    # Evict records older than 1 hour (3600 seconds)
    r.zremrangebyscore(receiver_recv_key, 0, now - 3600)

    # 3. Compute rolling window aggregates
    # 5-minute sender count (unique transactions sent)
    sender_5m_count = r.zcount(sender_sent_key, now - 300, now)

    # 30-minute receiver inflow
    receiver_30m_txns = r.zrangebyscore(receiver_recv_key, now - 1800, now)
    receiver_30m_inflow = sum(float(item.split(":")[-1]) for item in receiver_30m_txns)

    # 60-minute outflow/inflow for velocity
    sender_60m_txns = r.zrangebyscore(sender_sent_key, now - 3600, now)
    sent_60m_funds = sum(float(item.split(":")[-1]) for item in sender_60m_txns)

    receiver_60m_txns = r.zrangebyscore(receiver_recv_key, now - 3600, now)
    recv_60m_funds = sum(float(item.split(":")[-1]) for item in receiver_60m_txns)

    cash_out_velocity = sent_60m_funds / (recv_60m_funds + 1e-9)

    # Cache rolling window metrics to Redis hash map for quick pipeline lookup
    # Sender metrics
    r.hset(f"features:{sender}", mapping={
        "sender_5min_count": sender_5m_count,
        "cash_out_velocity": round(cash_out_velocity, 4)
    })
    # Receiver metrics
    r.hset(f"features:{receiver}", mapping={
        "receiver_30min_inflow": round(receiver_30m_inflow, 2),
    })

    return {
        "sender_5min_count": sender_5m_count,
        "receiver_30min_inflow": receiver_30m_inflow,
        "cash_out_velocity": cash_out_velocity
    }


def analyze_transaction(txn, redis_features):
    """
    Trigger full ML analysis on the FastAPI ML service if sliding windows look suspicious.
    """
    sender = txn.get("sender_account")
    receiver = txn.get("receiver_account")
    
    # Simple risk heuristic to prevent spamming analyze calls
    is_suspicious = (
        redis_features.get("sender_5min_count", 0) > 4 or
        redis_features.get("cash_out_velocity", 0.0) > 0.85 or
        float(txn.get("amount", 0.0)) > 50000.0
    )

    if not is_suspicious:
        return

    print(f"[Streaming] Suspicious activity detected on txn {txn.get('utr')}. Triggering ML analyze...")
    
    # Construct an IntakeRequest payload format for FastAPI /api/analyze
    payload = {
        "complaint": {
            "complaintId": f"STREAM-{int(time.time())}",
            "utr": txn.get("utr"),
            "amount": txn.get("amount"),
            "timestamp": txn.get("timestamp"),
            "firstBeneficiary": receiver
        },
        "transactions": [txn]
    }

    try:
        res = requests.post(f"{ML_URL}/api/analyze", json=payload, timeout=5)
        if res.status_code == 200:
            analysis = res.json()
            # If composite score of receiver is high, we can issue warnings
            rec_scores = analysis.get("mule_probabilities", {})
            score = rec_scores.get(receiver, 0.0) * 100.0
            print(f"[Streaming] Completed ML Analysis for receiver {receiver}. Score: {score:.1f}%")
        else:
            print(f"[Streaming] ML analysis failed with status: {res.status_code}")
    except Exception as e:
        print(f"[Streaming] Could not call ML service for live analysis: {e}")


def main():
    if not consumer:
        print("[Streaming] Kafka not available. Exiting streaming loop.")
        return

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(f"[Streaming] Kafka Error: {msg.error()}")
                    break

            try:
                txn = json.loads(msg.value().decode('utf-8'))
                print(f"[Streaming] Received transaction UTR: {txn.get('utr')} (Amount: ₹{txn.get('amount')})")
                
                # Update rolling window aggregates in Redis
                redis_features = update_redis_windows(txn)
                
                # Analyze if suspicious
                analyze_transaction(txn, redis_features)
                
            except Exception as e:
                print(f"[Streaming] Error processing message: {e}")

    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
