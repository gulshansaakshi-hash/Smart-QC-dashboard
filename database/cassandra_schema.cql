-- ============================================================================
-- Smart Manufacturing Quality Control & Anomaly Detection System
-- Apache Cassandra Keyspace & Table Schema
-- ============================================================================

-- Create keyspace for sensor time-series data
CREATE KEYSPACE IF NOT EXISTS manufacturing_data
WITH replication = {
    'class': 'SimpleStrategy',
    'replication_factor': 1
};

USE manufacturing_data;

-- ----------------------------------------------------------------------------
-- Table: sensor_readings
-- Primary Key Explanation:
--   machine_id is the PARTITION KEY so all readings for one machine are stored
--   together on the same partition.
--   timestamp is the CLUSTERING COLUMN sorted DESC (newest first), allowing
--   fast queries for the latest readings and recent history of any machine.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sensor_readings (
    machine_id TEXT,
    timestamp TIMESTAMP,
    temperature DOUBLE,
    vibration DOUBLE,
    pressure DOUBLE,
    rpm INT,
    power_consumption DOUBLE,
    production_speed INT,
    PRIMARY KEY ((machine_id), timestamp)
) WITH CLUSTERING ORDER BY (timestamp DESC);

