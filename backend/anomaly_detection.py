"""
Anomaly Detection Module.

Implements two beginner-friendly methods without machine learning libraries:
1. Threshold-based detection (IF/ELSE rules against configured operating ranges).
2. Z-score statistical detection for Temperature and Vibration:
       Z = (X - Mean) / Standard Deviation
   If |Z| > 3, the reading is classified as statistically unusual.
"""

import os
import sys
import math
import uuid

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import SENSOR_RANGES, MACHINE_RPM_RANGES
from backend.root_cause import identify_root_cause


def calculate_z_score(value, history_values):
    """
    Calculate the Z-score of `value` relative to `history_values`.

    Formula:
        Z = (X - Mean) / Standard Deviation

    Returns 0.0 if there are fewer than 5 historical samples or if
    standard deviation is 0 (all historical values are identical).
    """
    if not history_values or len(history_values) < 5:
        return 0.0

    n = len(history_values)
    mean = sum(history_values) / n
    variance = sum((x - mean) ** 2 for x in history_values) / n
    std_dev = math.sqrt(variance)

    if std_dev == 0:
        return 0.0

    return (value - mean) / std_dev


def _build_anomaly_record(machine_id, sensor_type, observed_value, normal_range, severity, timestamp, rca):
    """Create a standardized anomaly dictionary ready for MySQL insertion."""
    anomaly_id = f"ANOM-{uuid.uuid4().hex[:10].upper()}"
    return {
        "anomaly_id": anomaly_id,
        "machine_id": machine_id,
        "sensor_type": sensor_type,
        "observed_value": round(float(observed_value), 2),
        "normal_range": normal_range,
        "severity": severity,
        "possible_cause": rca["possible_cause"],
        "recommended_action": rca["recommended_action"],
        "detection_timestamp": timestamp,
        "alert_status": "Unresolved",
    }


def analyze_sensor_reading(reading, history_readings=None):
    """
    Analyze a single machine sensor reading using threshold rules and Z-score.

    Parameters:
        reading (dict): Current sensor values for one machine.
        history_readings (list[dict], optional): Recent readings for Z-score baseline.

    Returns:
        list[dict]: List of detected anomaly records (empty if all normal).
    """
    anomalies = []
    machine_id = reading["machine_id"]
    timestamp = reading["timestamp"]

    temp = float(reading["temperature"])
    vib = float(reading["vibration"])
    pres = float(reading["pressure"])
    rpm = int(reading["rpm"])

    temp_cfg = SENSOR_RANGES["temperature"]
    vib_cfg = SENSOR_RANGES["vibration"]
    pres_cfg = SENSOR_RANGES["pressure"]
    rpm_cfg = MACHINE_RPM_RANGES.get(machine_id, {"normal_min": 1000, "normal_max": 1800})

    # --- 1. Temperature Threshold Detection ---
    temp_range_str = f"{temp_cfg['normal_min']}–{temp_cfg['normal_max']} °C"
    if temp > temp_cfg["warning_max"]:  # > 85°C
        rca = identify_root_cause(reading, "Temperature")
        anomalies.append(
            _build_anomaly_record(machine_id, "Temperature", temp, temp_range_str, "Critical", timestamp, rca)
        )
    elif temp > temp_cfg["normal_max"]:  # 80–85°C
        rca = identify_root_cause(reading, "Temperature")
        anomalies.append(
            _build_anomaly_record(machine_id, "Temperature", temp, temp_range_str, "Medium", timestamp, rca)
        )
    elif temp < temp_cfg["normal_min"]:
        rca = identify_root_cause(reading, "Temperature")
        anomalies.append(
            _build_anomaly_record(machine_id, "Temperature", temp, temp_range_str, "Low", timestamp, rca)
        )

    # --- 2. Vibration Threshold Detection ---
    vib_range_str = f"{vib_cfg['normal_min']}–{vib_cfg['normal_max']} mm/s"
    if vib > vib_cfg["warning_max"]:  # > 7 mm/s
        rca = identify_root_cause(reading, "Vibration")
        anomalies.append(
            _build_anomaly_record(machine_id, "Vibration", vib, vib_range_str, "Critical", timestamp, rca)
        )
    elif vib > vib_cfg["normal_max"]:  # 6–7 mm/s
        rca = identify_root_cause(reading, "Vibration")
        anomalies.append(
            _build_anomaly_record(machine_id, "Vibration", vib, vib_range_str, "Medium", timestamp, rca)
        )

    # --- 3. Pressure Threshold Detection ---
    pres_range_str = f"{pres_cfg['normal_min']}–{pres_cfg['normal_max']} bar"
    if pres < pres_cfg["normal_min"]:  # < 4 bar
        rca = identify_root_cause(reading, "Pressure")
        anomalies.append(
            _build_anomaly_record(machine_id, "Pressure", pres, pres_range_str, "High", timestamp, rca)
        )
    elif pres > pres_cfg["normal_max"]:  # > 9 bar
        rca = identify_root_cause(reading, "Pressure")
        anomalies.append(
            _build_anomaly_record(machine_id, "Pressure", pres, pres_range_str, "High", timestamp, rca)
        )

    # --- 4. Machine-Specific RPM Detection ---
    rpm_range_str = f"{rpm_cfg['normal_min']}–{rpm_cfg['normal_max']} RPM"
    if rpm < rpm_cfg["normal_min"] or rpm > rpm_cfg["normal_max"]:
        rca = identify_root_cause(reading, "RPM")
        anomalies.append(
            _build_anomaly_record(machine_id, "RPM", rpm, rpm_range_str, "High", timestamp, rca)
        )

    # --- 5. Z-score Statistical Anomaly Detection (Temperature & Vibration) ---
    if history_readings:
        detected_types = {a["sensor_type"] for a in anomalies}

        if "Temperature" not in detected_types:
            temp_hist = [float(r["temperature"]) for r in history_readings]
            z_temp = calculate_z_score(temp, temp_hist)
            if abs(z_temp) > 3.0:
                rca = identify_root_cause(reading, "Z-Score")
                anomalies.append(
                    _build_anomaly_record(
                        machine_id,
                        "Temperature (Z-Score)",
                        temp,
                        f"|Z| <= 3.0 (Z={z_temp:.2f})",
                        "Medium",
                        timestamp,
                        rca,
                    )
                )

        if "Vibration" not in detected_types:
            vib_hist = [float(r["vibration"]) for r in history_readings]
            z_vib = calculate_z_score(vib, vib_hist)
            if abs(z_vib) > 3.0:
                rca = identify_root_cause(reading, "Z-Score")
                anomalies.append(
                    _build_anomaly_record(
                        machine_id,
                        "Vibration (Z-Score)",
                        vib,
                        f"|Z| <= 3.0 (Z={z_vib:.2f})",
                        "Medium",
                        timestamp,
                        rca,
                    )
                )

    return anomalies


def determine_machine_status(anomalies):
    """Return 'Critical', 'Warning', or 'Normal' based on detected anomalies."""
    if not anomalies:
        return "Normal"
    severities = {a["severity"] for a in anomalies}
    if "Critical" in severities or "High" in severities:
        return "Critical"
    return "Warning"

