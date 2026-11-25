-- ============================================================================
-- Smart Manufacturing Quality Control & Anomaly Detection System
-- MySQL Database Schema
-- Company: Precision Manufacturing Industries
-- ============================================================================

CREATE DATABASE IF NOT EXISTS smart_manufacturing;
USE smart_manufacturing;

-- ----------------------------------------------------------------------------
-- Table 1: production_lines
-- Stores the 3 manufacturing lines in the facility.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS production_lines (
    line_id VARCHAR(10) PRIMARY KEY,
    line_name VARCHAR(100) NOT NULL,
    description TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'Active'
);

-- ----------------------------------------------------------------------------
-- Table 2: machines
-- Stores the 5 manufacturing machines and their assigned production line.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS machines (
    machine_id VARCHAR(10) PRIMARY KEY,
    machine_name VARCHAR(100) NOT NULL,
    production_line VARCHAR(10) NOT NULL,
    machine_type VARCHAR(60) NOT NULL,
    operating_status VARCHAR(30) NOT NULL DEFAULT 'Normal',
    installation_date DATE NOT NULL,
    CONSTRAINT fk_machines_line
        FOREIGN KEY (production_line) REFERENCES production_lines(line_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- Table 3: customers
-- Stores fictional customer accounts placing manufacturing orders.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(15) PRIMARY KEY,
    customer_name VARCHAR(120) NOT NULL,
    contact_email VARCHAR(120) NOT NULL
);

-- ----------------------------------------------------------------------------
-- Table 4: customer_orders
-- Stores customer orders with product type, quantity, and quality tolerance.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customer_orders (
    order_id VARCHAR(15) PRIMARY KEY,
    customer_id VARCHAR(15) NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    required_quantity INT NOT NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'Medium',
    quality_requirement DECIMAL(5, 3) NOT NULL,
    order_date DATE NOT NULL,
    delivery_date DATE NOT NULL,
    order_status VARCHAR(30) NOT NULL DEFAULT 'In Progress',
    CONSTRAINT fk_orders_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- Table 5: production_records
-- Stores individual part/batch production events per machine and order.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS production_records (
    production_id VARCHAR(25) PRIMARY KEY,
    machine_id VARCHAR(10) NOT NULL,
    order_id VARCHAR(15) NOT NULL,
    part_id VARCHAR(30) NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    production_quantity INT NOT NULL DEFAULT 1,
    production_timestamp DATETIME NOT NULL,
    production_status VARCHAR(30) NOT NULL DEFAULT 'Completed',
    CONSTRAINT fk_production_machine
        FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_production_order
        FOREIGN KEY (order_id) REFERENCES customer_orders(order_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- Table 6: quality_inspections
-- Stores automated quality inspection results for manufactured parts.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS quality_inspections (
    inspection_id VARCHAR(25) PRIMARY KEY,
    part_id VARCHAR(30) NOT NULL,
    machine_id VARCHAR(10) NOT NULL,
    order_id VARCHAR(15) NOT NULL,
    dimensional_accuracy DECIMAL(6, 3) NOT NULL,
    surface_quality VARCHAR(30) NOT NULL,
    weight DECIMAL(8, 2) NOT NULL,
    inspection_result VARCHAR(10) NOT NULL,
    defect_category VARCHAR(60),
    inspection_timestamp DATETIME NOT NULL,
    CONSTRAINT fk_inspection_machine
        FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_inspection_order
        FOREIGN KEY (order_id) REFERENCES customer_orders(order_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- Table 7: anomalies
-- Stores detected sensor anomalies, severity, root cause, and alert status.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS anomalies (
    anomaly_id VARCHAR(30) PRIMARY KEY,
    machine_id VARCHAR(10) NOT NULL,
    sensor_type VARCHAR(40) NOT NULL,
    observed_value DECIMAL(10, 2) NOT NULL,
    normal_range VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    possible_cause TEXT NOT NULL,
    recommended_action TEXT NOT NULL,
    detection_timestamp DATETIME NOT NULL,
    alert_status VARCHAR(20) NOT NULL DEFAULT 'Unresolved',
    CONSTRAINT fk_anomalies_machine
        FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- Tableau Analytics View: production_quality_summary
-- Combines production, quality, machine, and line data for Tableau reporting.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW production_quality_summary AS
SELECT
    DATE(p.production_timestamp) AS production_date,
    m.machine_name,
    pl.line_name AS production_line,
    p.product_name,
    COUNT(p.production_id) AS total_production,
    SUM(CASE WHEN q.inspection_result = 'PASS' THEN 1 ELSE 0 END) AS good_parts,
    SUM(CASE WHEN q.inspection_result = 'FAIL' THEN 1 ELSE 0 END) AS defective_parts,
    ROUND(
        (SUM(CASE WHEN q.inspection_result = 'FAIL' THEN 1 ELSE 0 END) * 100.0) /
        NULLIF(COUNT(p.production_id), 0),
        2
    ) AS rejection_rate
FROM production_records p
JOIN machines m ON p.machine_id = m.machine_id
JOIN production_lines pl ON m.production_line = pl.line_id
LEFT JOIN quality_inspections q ON p.part_id = q.part_id
GROUP BY
    DATE(p.production_timestamp),
    m.machine_name,
    pl.line_name,
    p.product_name;

