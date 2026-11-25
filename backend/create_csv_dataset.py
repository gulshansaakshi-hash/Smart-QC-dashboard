"""
Standalone CSV Dataset Generator (Excel & Tableau compatible).

Generates a complete randomized manufacturing dataset in the `data/` folder
without requiring MySQL, Cassandra, or Kafka to be running:
  - data/machines.csv
  - data/customer_orders.csv
  - data/production_records.csv
  - data/quality_inspections.csv
  - data/sensor_readings.csv
  - data/anomalies.csv

Usage:
    python3 backend/create_csv_dataset.py
"""

import csv
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.data_generator import generate_initial_dataset, MACHINES
from backend.anomaly_detection import analyze_sensor_reading, determine_machine_status

DATA_DIR = os.path.join(PROJECT_ROOT, "data")


def _write_csv(filename, headers, rows):
    """Write rows to a UTF-8 CSV file (with BOM so Excel opens it cleanly)."""
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"[CSV Dataset] Created {filepath} ({len(rows)} rows)")
    return filepath


def create_all_csv_datasets():
    """Generate randomized dataset and save all tables as CSV files."""
    dataset = generate_initial_dataset()
    sensor_readings = dataset["sensor_readings"]

    # Analyze sensor readings per machine to detect anomalies & machine status
    machine_ids = [m[0] for m in MACHINES]
    by_machine = {mid: [] for mid in machine_ids}
    for r in sensor_readings:
        by_machine[r["machine_id"]].append(r)

    anomalies = []
    machine_status_map = {}
    for mid, readings in by_machine.items():
        latest_anoms = []
        for idx, reading in enumerate(readings):
            window = readings[max(0, idx - 30):idx]
            found = analyze_sensor_reading(reading, history_readings=window)
            anomalies.extend(found)
            if idx == len(readings) - 1:
                latest_anoms = found
        machine_status_map[mid] = determine_machine_status(latest_anoms)

    # 1. machines.csv
    machine_rows = [
        (m[0], m[1], m[2], m[3], machine_status_map.get(m[0], "Normal"), m[5])
        for m in dataset["machines"]
    ]
    _write_csv(
        "machines.csv",
        ["machine_id", "machine_name", "production_line", "machine_type", "operating_status", "installation_date"],
        machine_rows,
    )

    # 2. customer_orders.csv
    _write_csv(
        "customer_orders.csv",
        ["order_id", "customer_id", "product_name", "required_quantity", "priority", "quality_requirement", "order_date", "delivery_date", "order_status"],
        dataset["orders"],
    )

    # 3. production_records.csv
    _write_csv(
        "production_records.csv",
        ["production_id", "machine_id", "order_id", "part_id", "product_name", "production_quantity", "production_timestamp", "production_status"],
        dataset["production_records"],
    )

    # 4. quality_inspections.csv
    _write_csv(
        "quality_inspections.csv",
        ["inspection_id", "part_id", "machine_id", "order_id", "dimensional_accuracy", "surface_quality", "weight", "inspection_result", "defect_category", "inspection_timestamp"],
        dataset["quality_inspections"],
    )

    # 5. sensor_readings.csv
    sensor_rows = [
        (
            r["machine_id"],
            r["timestamp"],
            r["temperature"],
            r["vibration"],
            r["pressure"],
            r["rpm"],
            r["power"],
            r["production_speed"],
        )
        for r in sensor_readings
    ]
    _write_csv(
        "sensor_readings.csv",
        ["machine_id", "timestamp", "temperature", "vibration", "pressure", "rpm", "power_consumption", "production_speed"],
        sensor_rows,
    )

    # 6. anomalies.csv
    anomaly_rows = [
        (
            a["anomaly_id"],
            a["machine_id"],
            a["sensor_type"],
            a["observed_value"],
            a["normal_range"],
            a["severity"],
            a["possible_cause"],
            a["recommended_action"],
            a["detection_timestamp"],
            a["alert_status"],
        )
        for a in anomalies
    ]
    _write_csv(
        "anomalies.csv",
        ["anomaly_id", "machine_id", "sensor_type", "observed_value", "normal_range", "severity", "possible_cause", "recommended_action", "detection_timestamp", "alert_status"],
        anomaly_rows,
    )


if __name__ == "__main__":
    create_all_csv_datasets()

