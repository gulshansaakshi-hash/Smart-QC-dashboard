"""
Central configuration file for the Smart Manufacturing Quality Control
& Anomaly Detection System.

All database, Kafka, and sensor threshold settings are stored here
so they can be updated in one place without editing application code.
"""

import os

# Company information
COMPANY_NAME = "Precision Manufacturing Industries"

# MySQL Configuration (uses environment variables if set, otherwise local defaults)
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DATABASE", "smart_manufacturing"),
}

# Apache Cassandra Configuration
CASSANDRA_CONFIG = {
    "contact_points": os.environ.get("CASSANDRA_HOST", "127.0.0.1").split(","),
    "port": int(os.environ.get("CASSANDRA_PORT", 9042)),
    "keyspace": os.environ.get("CASSANDRA_KEYSPACE", "manufacturing_data"),
}

# Apache Kafka Configuration
KAFKA_CONFIG = {
    "bootstrap_servers": os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(","),
    "topic": os.environ.get("KAFKA_TOPIC", "machine_sensor_data"),
    "group_id": os.environ.get("KAFKA_GROUP_ID", "smart_manufacturing_group"),
}

# Flask Server Configuration
FLASK_CONFIG = {
    "host": os.environ.get("FLASK_HOST", "127.0.0.1"),
    "port": int(os.environ.get("FLASK_PORT", 5000)),
    "debug": True,
}

# Simulation Settings
SIMULATION_INTERVAL_SECONDS = 4  # Interval between live sensor readings (4-5 seconds)

# Configurable Sensor Operating Ranges
SENSOR_RANGES = {
    "temperature": {
        "unit": "°C",
        "normal_min": 40.0,
        "normal_max": 80.0,
        "warning_max": 85.0,
        "critical_max": 105.0,
    },
    "vibration": {
        "unit": "mm/s",
        "normal_min": 0.0,
        "normal_max": 6.0,
        "warning_max": 7.0,
        "critical_max": 12.0,
    },
    "pressure": {
        "unit": "bar",
        "normal_min": 4.0,
        "normal_max": 9.0,
        "low_limit": 2.0,
        "high_limit": 12.0,
    },
    "power": {
        "unit": "kW",
        "normal_min": 2.0,
        "normal_max": 15.0,
    },
    "production_speed": {
        "unit": "units/hour",
        "normal_min": 20,
        "normal_max": 100,
        "low_threshold": 25,
    },
}

# Machine-specific RPM ranges
MACHINE_RPM_RANGES = {
    "M001": {"normal_min": 1200, "normal_max": 1800},
    "M002": {"normal_min": 800, "normal_max": 1400},
    "M003": {"normal_min": 1000, "normal_max": 1600},
    "M004": {"normal_min": 1800, "normal_max": 2600},
    "M005": {"normal_min": 1300, "normal_max": 1900},
}

# Standard defect categories for quality inspection
DEFECT_CATEGORIES = [
    "Dimensional Defect",
    "Surface Defect",
    "Weight Variation",
    "Material Defect",
    "Manufacturing Error",
]

