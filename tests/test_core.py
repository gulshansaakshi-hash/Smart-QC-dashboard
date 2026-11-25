"""
Unit Tests for Core Python Modules (Data Generation, Anomaly Detection,
Root Cause Analysis, and Quality Inspection).

Run with:
    python3 -m unittest discover -s tests -v
"""

import os
import sys
import unittest
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.data_generator import generate_initial_dataset, inspect_part
from backend.anomaly_detection import (
    analyze_sensor_reading,
    calculate_z_score,
    determine_machine_status,
)
from backend.root_cause import identify_root_cause


class TestSmartManufacturing(unittest.TestCase):
    """Verifies core simulation, anomaly detection, RCA, and quality logic."""

    def test_1_initial_data_generation(self):
        dataset = generate_initial_dataset()
        self.assertEqual(len(dataset["production_lines"]), 3)
        self.assertEqual(len(dataset["machines"]), 5)
        self.assertEqual(len(dataset["orders"]), 15)
        self.assertEqual(len(dataset["production_records"]), 500)
        self.assertEqual(len(dataset["quality_inspections"]), 500)
        self.assertGreaterEqual(len(dataset["sensor_readings"]), 1000)

    def test_2_normal_sensor_readings(self):
        normal_reading = {
            "machine_id": "M001",
            "temperature": 65.0,
            "vibration": 3.0,
            "pressure": 6.5,
            "rpm": 1500,
            "power": 8.0,
            "production_speed": 60,
            "timestamp": "2026-11-25 10:00:00",
        }
        anomalies = analyze_sensor_reading(normal_reading)
        self.assertEqual(anomalies, [])
        self.assertEqual(determine_machine_status(anomalies), "Normal")

    def test_3_high_temperature_critical(self):
        hot_reading = {
            "machine_id": "M001",
            "temperature": 92.0,
            "vibration": 3.5,
            "pressure": 6.5,
            "rpm": 1500,
            "power": 9.0,
            "production_speed": 55,
            "timestamp": "2026-11-25 10:05:00",
        }
        anomalies = analyze_sensor_reading(hot_reading)
        self.assertTrue(any(a["sensor_type"] == "Temperature" and a["severity"] == "Critical" for a in anomalies))
        self.assertEqual(determine_machine_status(anomalies), "Critical")

    def test_4_high_vibration_critical(self):
        vib_reading = {
            "machine_id": "M002",
            "temperature": 70.0,
            "vibration": 8.5,
            "pressure": 6.5,
            "rpm": 1100,
            "power": 8.5,
            "production_speed": 55,
            "timestamp": "2026-11-25 10:10:00",
        }
        anomalies = analyze_sensor_reading(vib_reading)
        self.assertTrue(any(a["sensor_type"] == "Vibration" and a["severity"] == "Critical" for a in anomalies))

    def test_5_root_cause_bearing_wear(self):
        reading = {
            "machine_id": "M005",
            "temperature": 92.0,
            "vibration": 8.5,
            "pressure": 6.5,
            "rpm": 1600,
            "power": 10.0,
            "production_speed": 50,
            "timestamp": "2026-11-25 10:15:00",
        }
        rca = identify_root_cause(reading)
        self.assertIn("Bearing wear", rca["possible_cause"])
        self.assertIn("lubrication", rca["recommended_action"].lower())

    def test_6_z_score_outlier_detection(self):
        history = [60.0, 61.0, 59.5, 60.5, 60.2, 59.8, 60.1, 60.4, 59.9, 60.0]
        z = calculate_z_score(78.0, history)
        self.assertGreater(abs(z), 3.0)

    def test_7_quality_inspection_output(self):
        now = datetime.now()
        results = [
            inspect_part(f"PART{i}", "M001", "ORD001", "Industrial Gear A", 0.050, now)
            for i in range(40)
        ]
        self.assertTrue(all(r["inspection_result"] in ("PASS", "FAIL") for r in results))


if __name__ == "__main__":
    unittest.main()

