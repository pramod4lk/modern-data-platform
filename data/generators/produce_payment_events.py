"""Produce synthetic payment events to Kafka (JSON), keyed by institution_id.

Run from a machine that can reach Kafka, e.g. with a port-forward:
    kubectl -n streaming port-forward svc/poc-kafka-kafka-bootstrap 9092:9092
    pip install kafka-python-ng
    python data/generators/produce_payment_events.py --rate 20 --duration 300

Note: through a port-forward the broker may advertise its in-cluster address. If producing fails,
run this script inside the cluster instead (e.g. a python:3.12 pod in the streaming namespace).
"""

from __future__ import annotations

import argparse
import json
import random
import time
import uuid

from kafka import KafkaProducer

SYSTEMS = ["RTGS", "INSTANT", "CARD", "CHEQUE"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--bootstrap", default="localhost:9092")
    p.add_argument("--topic", default="payments.events.v1")
    p.add_argument("--rate", type=float, default=10, help="events per second")
    p.add_argument("--duration", type=int, default=60, help="seconds")
    p.add_argument("--institutions", type=int, default=10)
    p.add_argument("--late-ratio", type=float, default=0.02, help="share of events 1-4 minutes late")
    p.add_argument("--duplicate-ratio", type=float, default=0.01)
    a = p.parse_args()

    producer = KafkaProducer(
        bootstrap_servers=a.bootstrap,
        key_serializer=str.encode,
        value_serializer=lambda v: json.dumps(v).encode(),
        acks="all",
        enable_idempotence=True,
    )
    end = time.time() + a.duration
    sent = 0
    while time.time() < end:
        inst = f"FI{random.randint(1, a.institutions):03d}"
        ts = int(time.time() * 1000)
        if random.random() < a.late_ratio:
            ts -= random.randint(60_000, 240_000)
        event = {
            "event_id": str(uuid.uuid4()),
            "institution_id": inst,
            "event_time": ts,
            "payment_system": random.choice(SYSTEMS),
            "direction": random.choice(["OUT", "IN"]),
            "amount": round(random.lognormvariate(8, 1.5), 2),
            "currency": "MYR",
            "status": random.choices(["SETTLED", "PENDING", "FAILED"], [0.95, 0.04, 0.01])[0],
        }
        producer.send(a.topic, key=inst, value=event)
        if random.random() < a.duplicate_ratio:
            producer.send(a.topic, key=inst, value=event)
        sent += 1
        time.sleep(1 / a.rate)
    producer.flush()
    print(f"sent {sent} events to {a.topic}")


if __name__ == "__main__":
    main()
