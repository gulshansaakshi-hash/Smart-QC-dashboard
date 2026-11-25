"""
Apache Kafka Producer for simulated machine sensor streaming.

Generates sensor readings for the 5 manufacturing machines and publishes
JSON messages to the `machine_sensor_data` topic every 4-5 seconds.

Can be run standalone:
    python3 backend/kafka_producer.py
or controlled from the Flask backend via start_producer() / stop_producer().
"""

import json
import os
import sys
import threading
import time
from datetime import datetime

from kafka import KafkaProducer

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import KAFKA_CONFIG, SIMULATION_INTERVAL_SECONDS
from backend.data_generator import MACHINES, generate_single_sensor_reading

_producer_thread = None
_stop_event = threading.Event()


def create_kafka_producer():
    """Create and return a KafkaProducer configured for JSON messages."""
    return KafkaProducer(
        bootstrap_servers=KAFKA_CONFIG["bootstrap_servers"],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )


def run_producer_loop(stop_event=None):
    """
    Continuously generate and publish sensor readings to Kafka every 4-5 seconds.
    Periodically forces a high-temperature or high-vibration condition so
    anomaly detection can be demonstrated reliably.
    """
    if stop_event is None:
        stop_event = threading.Event()

    producer = create_kafka_producer()
    topic = KAFKA_CONFIG["topic"]
    cycle = 0

    print(f"[Kafka Producer] Started publishing to topic '{topic}'...")
    try:
        while not stop_event.is_set():
            cycle += 1
            for idx, machine in enumerate(MACHINES):
                machine_id = machine[0]
                # Every 4th cycle, simulate a fault on M002 or M005 for demonstration
                force_fault = (cycle % 4 == 0) and (machine_id in ("M002", "M005"))
                reading = generate_single_sensor_reading(
                    machine_id,
                    timestamp=datetime.now(),
                    force_anomaly=force_fault,
                )
                producer.send(topic, value=reading)
                print(
                    f"[Kafka Producer] Sent {machine_id} | "
                    f"Temp={reading['temperature']}°C, Vib={reading['vibration']}mm/s"
                )
            producer.flush()
            stop_event.wait(SIMULATION_INTERVAL_SECONDS)
    finally:
        producer.close()
        print("[Kafka Producer] Stopped.")


def start_producer():
    """Start the Kafka producer in a single background thread."""
    global _producer_thread
    if _producer_thread is not None and _producer_thread.is_alive():
        return False

    _stop_event.clear()
    _producer_thread = threading.Thread(
        target=run_producer_loop,
        args=(_stop_event,),
        daemon=True,
    )
    _producer_thread.start()
    return True


def stop_producer():
    """Signal the background Kafka producer thread to stop."""
    global _producer_thread
    _stop_event.set()
    if _producer_thread is not None:
        _producer_thread.join(timeout=2)
        _producer_thread = None
    return True


def is_producer_running():
    """Return True if the background producer thread is active."""
    return _producer_thread is not None and _producer_thread.is_alive()


if __name__ == "__main__":
    try:
        run_producer_loop()
    except KeyboardInterrupt:
        print("\n[Kafka Producer] Interrupted by user.")

