"""
Apache Cassandra helper module for storing and querying time-series sensor readings.

Keyspace: manufacturing_data
Table:    sensor_readings
Primary Key: PRIMARY KEY ((machine_id), timestamp) WITH CLUSTERING ORDER BY (timestamp DESC)
"""

import os
import sys
from datetime import datetime
from cassandra.cluster import Cluster

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import CASSANDRA_CONFIG

_cluster = None
_session = None


def get_session():
    """Connect to the Cassandra cluster and return a reusable session."""
    global _cluster, _session
    if _session is not None:
        return _session

    _cluster = Cluster(
        contact_points=CASSANDRA_CONFIG["contact_points"],
        port=CASSANDRA_CONFIG["port"],
    )
    _session = _cluster.connect()
    init_cassandra_schema(_session)
    _session.set_keyspace(CASSANDRA_CONFIG["keyspace"])
    return _session


def init_cassandra_schema(session=None):
    """Create the manufacturing_data keyspace and sensor_readings table if missing."""
    if session is None:
        session = get_session()

    keyspace = CASSANDRA_CONFIG["keyspace"]
    session.execute(
        f"""
        CREATE KEYSPACE IF NOT EXISTS {keyspace}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
        """
    )
    # Primary key partitions by machine_id and clusters by timestamp DESC (newest first)
    session.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {keyspace}.sensor_readings (
            machine_id TEXT,
            timestamp TIMESTAMP,
            temperature DOUBLE,
            vibration DOUBLE,
            pressure DOUBLE,
            rpm INT,
            power_consumption DOUBLE,
            production_speed INT,
            PRIMARY KEY ((machine_id), timestamp)
        ) WITH CLUSTERING ORDER BY (timestamp DESC)
        """
    )


def _parse_timestamp(ts_value):
    """Convert string timestamp to Python datetime for Cassandra TIMESTAMP column."""
    if isinstance(ts_value, datetime):
        return ts_value
    return datetime.strptime(ts_value, "%Y-%m-%d %H:%M:%S")


def insert_sensor_reading(reading):
    """Insert a single sensor reading dictionary into Cassandra."""
    session = get_session()
    query = """
        INSERT INTO sensor_readings (
            machine_id, timestamp, temperature, vibration,
            pressure, rpm, power_consumption, production_speed
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    session.execute(
        query,
        (
            reading["machine_id"],
            _parse_timestamp(reading["timestamp"]),
            float(reading["temperature"]),
            float(reading["vibration"]),
            float(reading["pressure"]),
            int(reading["rpm"]),
            float(reading["power"]),
            int(reading["production_speed"]),
        ),
    )


def insert_sensor_readings_batch(readings):
    """Insert multiple sensor readings into Cassandra."""
    if not readings:
        return
    session = get_session()
    prepared = session.prepare(
        """
        INSERT INTO sensor_readings (
            machine_id, timestamp, temperature, vibration,
            pressure, rpm, power_consumption, production_speed
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
    )
    for reading in readings:
        session.execute(
            prepared,
            (
                reading["machine_id"],
                _parse_timestamp(reading["timestamp"]),
                float(reading["temperature"]),
                float(reading["vibration"]),
                float(reading["pressure"]),
                int(reading["rpm"]),
                float(reading["power"]),
                int(reading["production_speed"]),
            ),
        )


def _row_to_dict(row):
    """Convert a Cassandra Row object into a JSON-serializable dictionary."""
    return {
        "machine_id": row.machine_id,
        "timestamp": row.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "temperature": round(float(row.temperature), 2),
        "vibration": round(float(row.vibration), 2),
        "pressure": round(float(row.pressure), 2),
        "rpm": int(row.rpm),
        "power": round(float(row.power_consumption), 2),
        "production_speed": int(row.production_speed),
    }


def get_latest_reading(machine_id):
    """Retrieve the single most recent sensor reading for a machine."""
    history = get_sensor_history(machine_id, limit=1)
    return history[0] if history else None


def get_latest_readings_all_machines(machine_ids):
    """Retrieve the latest reading for each machine in machine_ids."""
    latest = {}
    for mid in machine_ids:
        reading = get_latest_reading(mid)
        if reading:
            latest[mid] = reading
    return latest


def get_sensor_history(machine_id, limit=50):
    """Retrieve recent sensor history for a machine, ordered newest-first."""
    session = get_session()
    query = """
        SELECT machine_id, timestamp, temperature, vibration,
               pressure, rpm, power_consumption, production_speed
        FROM sensor_readings
        WHERE machine_id = %s
        LIMIT %s
    """
    rows = session.execute(query, (machine_id, int(limit)))
    return [_row_to_dict(row) for row in rows]


def clear_sensor_readings(machine_ids=None):
    """Delete sensor readings for the given machines (used during Demo Reset)."""
    session = get_session()
    if machine_ids is None:
        session.execute("TRUNCATE sensor_readings")
    else:
        for mid in machine_ids:
            session.execute("DELETE FROM sensor_readings WHERE machine_id = %s", (mid,))


def test_cassandra_connection():
    """Return True if Cassandra is reachable."""
    try:
        get_session()
        return True
    except Exception:
        return False

