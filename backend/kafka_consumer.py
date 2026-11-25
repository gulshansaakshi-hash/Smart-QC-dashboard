"""
Apache Kafka Consumer for real-time machine sensor processing.

Subscribes to topic `machine_sensor_data`, stores incoming sensor readings in
Apache Cassandra, runs Python anomaly detection, and saves detected anomalies
to MySQL.

Can be run standalone:
    python3 backend/kafka_consumer.py
or started in a background thread from the Flask backend.
"""

import json
import os
import sys
import threading

from kafka import KafkaConsumer

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import KAFKA_CONFIG
from backend import cassandra_db, mysql_db
from backend.anomaly_detection import analyze_sensor_reading, determine_machine_status

_consumer_thread = None
_stop_event = threading.Event()


def create_kafka_consumer():
    """Create and return a KafkaConsumer subscribed to `machine_sensor_data`."""
    return KafkaConsumer(
        KAFKA_CONFIG["topic"],
        bootstrap_servers=KAFKA_CONFIG["bootstrap_servers"],
        group_id=KAFKA_CONFIG["group_id"],
        auto_offset_reset="latest",
        enable_auto_commit=True,
        consumer_timeout_ms=1000,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )


def process_sensor_message(reading):
    """
    Process a single sensor JSON message:
    1. Store reading in Apache Cassandra.
    2. Fetch recent machine history for Z-score baseline.
    3. Run threshold + Z-score anomaly detection.
    4. Store detected anomalies and update machine status in MySQL.
    """
    machine_id = reading["machine_id"]

    # Step 1: Store in Cassandra
    cassandra_db.insert_sensor_reading(reading)

    # Step 2: Fetch recent history for Z-score calculation
    history = cassandra_db.get_sensor_history(machine_id, limit=30)

    # Step 3: Detect anomalies
    anomalies = analyze_sensor_reading(reading, history_readings=history)

    # Step 4: Store anomalies & update machine status in MySQL
    status = determine_machine_status(anomalies)
    mysql_db.update_machine_status(machine_id, status)

    if anomalies:
        mysql_db.insert_anomalies_batch(anomalies)
        for anom in anomalies:
            print(
                f"Machine {machine_id}: {anom['sensor_type']} Anomaly Detected "
                f"({anom['observed_value']}, Severity: {anom['severity']})"
            )
    else:
        print(f"Machine {machine_id}: Sensor Reading Stored (Status: Normal)")

    return anomalies


def run_consumer_loop(stop_event=None):
    """Continuously poll Kafka for sensor messages until stop_event is set."""
    if stop_event is None:
        stop_event = threading.Event()

    consumer = create_kafka_consumer()
    print(f"[Kafka Consumer] Listening on topic '{KAFKA_CONFIG['topic']}'...")
    try:
        while not stop_event.is_set():
            for message in consumer:
                if stop_event.is_set():
                    break
                process_sensor_message(message.value)
    finally:
        consumer.close()
        print("[Kafka Consumer] Stopped.")


def start_consumer():
    """Start the Kafka consumer in a single background thread."""
    global _consumer_thread
    if _consumer_thread is not None and _consumer_thread.is_alive():
        return False

    _stop_event.clear()
    _consumer_thread = threading.Thread(
        target=run_consumer_loop,
        args=(_stop_event,),
        daemon=True,
    )
    _consumer_thread.start()
    return True


def stop_consumer():
    """Signal the background Kafka consumer thread to stop."""
    global _consumer_thread
    _stop_event.set()
    if _consumer_thread is not None:
        _consumer_thread.join(timeout=2)
        _consumer_thread = None
    return True


if __name__ == "__main__":
    try:
        run_consumer_loop()
    except KeyboardInterrupt:
        print("\n[Kafka Consumer] Interrupted by user.")

