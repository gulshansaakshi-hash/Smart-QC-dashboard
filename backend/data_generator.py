"""
Automatic Data Generator for Precision Manufacturing Industries.

Generates simulated:
- 3 Production Lines
- 5 Manufacturing Machines
- 6 Customers and 15 Customer Orders
- 500 Production Records (last 24 hours)
- 500 Quality Inspection Records (using customer-specific tolerances)
- 1,050+ Sensor Readings (85% normal, 15% abnormal)

Uses Python's built-in random and datetime modules so the logic is easy
to understand and explain.
"""

import os
import sys
import random
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import SENSOR_RANGES, MACHINE_RPM_RANGES, DEFECT_CATEGORIES

# Static facility master data
PRODUCTION_LINES = [
    ("L001", "Gear Manufacturing", "High-precision industrial gear cutting and CNC machining", "Active"),
    ("L002", "Bearing Manufacturing", "Ball and roller bearing assembly and surface grinding", "Active"),
    ("L003", "Precision Components", "Custom precision shafts and machined metal components", "Active"),
]

MACHINES = [
    ("M001", "CNC Machine 01", "L001", "CNC Machining Center", "Normal", "2023-03-15"),
    ("M002", "Gear Cutting Machine 01", "L001", "Gear Hobbing Machine", "Normal", "2023-05-20"),
    ("M003", "Bearing Assembly Machine 01", "L002", "Automated Assembly Press", "Normal", "2023-07-10"),
    ("M004", "Grinding Machine 01", "L002", "Cylindrical Grinder", "Normal", "2024-01-12"),
    ("M005", "CNC Machine 02", "L003", "5-Axis CNC Lathe", "Normal", "2024-04-05"),
]

MACHINE_PRODUCTS = {
    "M001": ["Industrial Gear A", "Industrial Gear B"],
    "M002": ["Industrial Gear A", "Industrial Gear B"],
    "M003": ["Ball Bearing", "Roller Bearing"],
    "M004": ["Ball Bearing", "Roller Bearing"],
    "M005": ["Precision Shaft", "Metal Component"],
}

PRODUCT_SPECS = {
    "Industrial Gear A": {"target_weight": 420.0, "machines": ["M001", "M002"]},
    "Industrial Gear B": {"target_weight": 540.0, "machines": ["M001", "M002"]},
    "Ball Bearing": {"target_weight": 180.0, "machines": ["M003", "M004"]},
    "Roller Bearing": {"target_weight": 260.0, "machines": ["M003", "M004"]},
    "Precision Shaft": {"target_weight": 680.0, "machines": ["M005"]},
    "Metal Component": {"target_weight": 310.0, "machines": ["M005"]},
}

CUSTOMERS = [
    ("CUST001", "Apex Automotive Ltd", "procurement@apexauto.example.com"),
    ("CUST002", "Titan Heavy Engineering", "orders@titanheavy.example.com"),
    ("CUST003", "Velocity Robotics Inc", "supply@velocityrobotics.example.com"),
    ("CUST004", "Nordic Wind Turbines", "quality@nordicwind.example.com"),
    ("CUST005", "Metro Rail Systems", "parts@metrorail.example.com"),
    ("CUST006", "Horizon Aerospace Co", "sourcing@horizonaero.example.com"),
]

# Machines that occasionally develop faults vs machines that stay mostly healthy
FAULT_PRONE_MACHINES = {"M002": 0.22, "M004": 0.18, "M005": 0.25, "M001": 0.05, "M003": 0.05}


def generate_customer_orders(base_time=None):
    """Create 15 sample customer orders with varying tolerances (0.05, 0.10, 0.15 mm)."""
    if base_time is None:
        base_time = datetime.now()

    products = list(PRODUCT_SPECS.keys())
    priorities = ["High", "Medium", "Low"]
    tolerances = [0.050, 0.100, 0.150]
    statuses = ["In Progress", "In Progress", "In Progress", "Completed", "Pending"]

    orders = []
    for i in range(1, 16):
        order_id = f"ORD{i:03d}"
        customer_id = CUSTOMERS[(i - 1) % len(CUSTOMERS)][0]
        product_name = products[(i - 1) % len(products)]
        required_qty = random.choice([200, 250, 300, 400, 500])
        priority = priorities[(i - 1) % len(priorities)]
        tolerance = tolerances[(i - 1) % len(tolerances)]
        order_date = (base_time - timedelta(days=random.randint(2, 10))).strftime("%Y-%m-%d")
        delivery_date = (base_time + timedelta(days=random.randint(3, 14))).strftime("%Y-%m-%d")
        status = statuses[(i - 1) % len(statuses)]

        orders.append((
            order_id,
            customer_id,
            product_name,
            required_qty,
            priority,
            tolerance,
            order_date,
            delivery_date,
            status,
        ))
    return orders


def generate_single_sensor_reading(machine_id, timestamp=None, force_anomaly=False):
    """
    Generate one realistic sensor reading dictionary for a machine.
    Roughly 85% normal and 15% abnormal overall (higher chance on fault-prone machines).
    """
    if timestamp is None:
        timestamp = datetime.now()

    rpm_cfg = MACHINE_RPM_RANGES[machine_id]
    temp_cfg = SENSOR_RANGES["temperature"]
    vib_cfg = SENSOR_RANGES["vibration"]
    pres_cfg = SENSOR_RANGES["pressure"]
    pwr_cfg = SENSOR_RANGES["power"]
    spd_cfg = SENSOR_RANGES["production_speed"]

    # Normal baseline values
    temperature = round(random.uniform(52.0, 74.0), 2)
    vibration = round(random.uniform(1.2, 4.8), 2)
    pressure = round(random.uniform(5.0, 8.2), 2)
    rpm = random.randint(rpm_cfg["normal_min"] + 50, rpm_cfg["normal_max"] - 50)
    power = round(random.uniform(4.5, 12.5), 2)
    production_speed = random.randint(45, 88)

    anomaly_prob = FAULT_PRONE_MACHINES.get(machine_id, 0.15)
    is_abnormal = force_anomaly or (random.random() < anomaly_prob)

    if is_abnormal:
        scenario = random.choice([
            "bearing_wear",
            "overheating",
            "shaft_misalignment",
            "low_pressure",
            "high_pressure",
            "warning_temp",
        ])
        if scenario == "bearing_wear":
            temperature = round(random.uniform(86.0, 96.0), 2)
            vibration = round(random.uniform(7.4, 9.8), 2)
        elif scenario == "overheating":
            temperature = round(random.uniform(86.0, 95.0), 2)
            production_speed = random.randint(12, 22)
        elif scenario == "shaft_misalignment":
            vibration = round(random.uniform(7.3, 9.5), 2)
            rpm = rpm_cfg["normal_max"] + random.randint(150, 350)
        elif scenario == "low_pressure":
            pressure = round(random.uniform(2.2, 3.7), 2)
        elif scenario == "high_pressure":
            pressure = round(random.uniform(9.4, 11.2), 2)
        else:
            temperature = round(random.uniform(temp_cfg["normal_max"] + 0.5, temp_cfg["warning_max"] - 0.3), 2)
            vibration = round(random.uniform(vib_cfg["normal_max"] + 0.2, vib_cfg["warning_max"] - 0.2), 2)

    return {
        "machine_id": machine_id,
        "temperature": temperature,
        "vibration": vibration,
        "pressure": pressure,
        "rpm": rpm,
        "power": power,
        "production_speed": production_speed,
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
    }


def inspect_part(part_id, machine_id, order_id, product_name, tolerance, timestamp):
    """
    Automated Quality Inspection logic:
    PASS if dimensional deviation <= customer tolerance AND surface_quality is acceptable
    AND weight is within +/- 5% of target weight. Otherwise FAIL with a defect category.
    """
    target_weight = PRODUCT_SPECS[product_name]["target_weight"]

    # ~88% pass rate, ~12% defect rate
    will_fail = random.random() < 0.12

    if not will_fail:
        dimensional_accuracy = round(random.uniform(-tolerance * 0.8, tolerance * 0.8), 3)
        surface_quality = random.choice(["Excellent", "Good", "Acceptable"])
        weight = round(target_weight * random.uniform(0.97, 1.03), 2)
        inspection_result = "PASS"
        defect_category = None
    else:
        defect_category = random.choice(DEFECT_CATEGORIES)
        if defect_category == "Dimensional Defect":
            sign = random.choice([-1, 1])
            dimensional_accuracy = round(sign * (tolerance + random.uniform(0.02, 0.12)), 3)
            surface_quality = "Good"
            weight = round(target_weight * random.uniform(0.98, 1.02), 2)
        elif defect_category == "Surface Defect":
            dimensional_accuracy = round(random.uniform(-tolerance * 0.7, tolerance * 0.7), 3)
            surface_quality = "Poor"
            weight = round(target_weight * random.uniform(0.98, 1.02), 2)
        elif defect_category == "Weight Variation":
            dimensional_accuracy = round(random.uniform(-tolerance * 0.7, tolerance * 0.7), 3)
            surface_quality = "Acceptable"
            weight = round(target_weight * random.choice([0.89, 1.11]), 2)
        else:
            dimensional_accuracy = round(random.uniform(-tolerance * 1.4, tolerance * 1.4), 3)
            surface_quality = random.choice(["Poor", "Acceptable"])
            weight = round(target_weight * random.uniform(0.93, 1.07), 2)

        inspection_result = "FAIL"

    return {
        "part_id": part_id,
        "machine_id": machine_id,
        "order_id": order_id,
        "dimensional_accuracy": dimensional_accuracy,
        "surface_quality": surface_quality,
        "weight": weight,
        "inspection_result": inspection_result,
        "defect_category": defect_category,
        "inspection_timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
    }


def generate_production_and_quality_records(orders, count=500, start_index=1, hours_back=24, base_time=None):
    """Generate matching production_records and quality_inspections tuples."""
    if base_time is None:
        base_time = datetime.now()

    production_rows = []
    inspection_rows = []

    for idx in range(start_index, start_index + count):
        order = random.choice(orders)
        order_id = order[0]
        product_name = order[2]
        tolerance = float(order[5])
        machine_id = random.choice(PRODUCT_SPECS[product_name]["machines"])

        # Distribute timestamps across the requested time window
        offset_seconds = random.randint(0, hours_back * 3600)
        ts = base_time - timedelta(seconds=offset_seconds)
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")

        prod_id = f"PROD{idx:05d}"
        part_id = f"PART{idx:05d}"
        insp_id = f"INSP{idx:05d}"

        production_rows.append((
            prod_id,
            machine_id,
            order_id,
            part_id,
            product_name,
            1,
            ts_str,
            "Completed",
        ))

        insp = inspect_part(part_id, machine_id, order_id, product_name, tolerance, ts)
        inspection_rows.append((
            insp_id,
            insp["part_id"],
            insp["machine_id"],
            insp["order_id"],
            insp["dimensional_accuracy"],
            insp["surface_quality"],
            insp["weight"],
            insp["inspection_result"],
            insp["defect_category"],
            insp["inspection_timestamp"],
        ))

    return production_rows, inspection_rows


def generate_historical_sensor_readings(readings_per_machine=210, hours_back=24, base_time=None):
    """
    Generate 1,050+ sensor readings across all 5 machines over the previous 24 hours.
    """
    if base_time is None:
        base_time = datetime.now()

    all_readings = []
    step_seconds = int((hours_back * 3600) / readings_per_machine)

    for machine in MACHINES:
        machine_id = machine[0]
        for i in range(readings_per_machine):
            ts = base_time - timedelta(seconds=(readings_per_machine - i) * step_seconds)
            reading = generate_single_sensor_reading(machine_id, timestamp=ts)
            all_readings.append(reading)

    return all_readings


def generate_initial_dataset():
    """Build the complete initial dataset (500 prod, 500 quality, 1050 sensor readings)."""
    now = datetime.now()
    orders = generate_customer_orders(base_time=now)
    production_rows, inspection_rows = generate_production_and_quality_records(
        orders, count=500, start_index=1, hours_back=24, base_time=now
    )
    sensor_readings = generate_historical_sensor_readings(
        readings_per_machine=210, hours_back=24, base_time=now
    )

    return {
        "production_lines": PRODUCTION_LINES,
        "machines": MACHINES,
        "customers": CUSTOMERS,
        "orders": orders,
        "production_records": production_rows,
        "quality_inspections": inspection_rows,
        "sensor_readings": sensor_readings,
    }

