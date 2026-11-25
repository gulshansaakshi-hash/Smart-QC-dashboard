"""
MySQL database helper module for the Smart Manufacturing Quality Control system.

Handles connections, schema initialization, inserts, queries, and alert updates
for the `smart_manufacturing` database.
"""

import os
import sys
import mysql.connector
from mysql.connector import Error

# Allow importing config.py from the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import MYSQL_CONFIG


def get_connection(use_database=True):
    """Create and return a new MySQL database connection."""
    conn_params = {
        "host": MYSQL_CONFIG["host"],
        "port": MYSQL_CONFIG["port"],
        "user": MYSQL_CONFIG["user"],
        "password": MYSQL_CONFIG["password"],
    }
    if use_database:
        conn_params["database"] = MYSQL_CONFIG["database"]
    return mysql.connector.connect(**conn_params)


def init_database():
    """Execute database/database.sql to create the database, tables, and view."""
    sql_path = os.path.join(PROJECT_ROOT, "database", "database.sql")
    with open(sql_path, "r", encoding="utf-8") as f:
        sql_script = f.read()

    conn = get_connection(use_database=False)
    cursor = conn.cursor()
    try:
        # Split on ';' to execute each SQL statement cleanly
        for statement in sql_script.split(";"):
            stmt = statement.strip()
            if stmt:
                cursor.execute(stmt)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def clear_all_data():
    """Delete all rows from MySQL tables in foreign-key-safe order."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        tables = [
            "anomalies",
            "quality_inspections",
            "production_records",
            "customer_orders",
            "customers",
            "machines",
            "production_lines",
        ]
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def insert_production_lines(lines):
    """Insert or update production line records."""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO production_lines (line_id, line_name, description, status)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            line_name = VALUES(line_name),
            description = VALUES(description),
            status = VALUES(status)
    """
    try:
        cursor.executemany(query, lines)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def insert_machines(machines):
    """Insert or update machine records."""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO machines (
            machine_id, machine_name, production_line,
            machine_type, operating_status, installation_date
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            machine_name = VALUES(machine_name),
            production_line = VALUES(production_line),
            machine_type = VALUES(machine_type),
            operating_status = VALUES(operating_status),
            installation_date = VALUES(installation_date)
    """
    try:
        cursor.executemany(query, machines)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def insert_customers(customers):
    """Insert or update customer records."""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO customers (customer_id, customer_name, contact_email)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            customer_name = VALUES(customer_name),
            contact_email = VALUES(contact_email)
    """
    try:
        cursor.executemany(query, customers)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def insert_customer_orders(orders):
    """Insert or update customer order records."""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO customer_orders (
            order_id, customer_id, product_name, required_quantity,
            priority, quality_requirement, order_date, delivery_date, order_status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            product_name = VALUES(product_name),
            required_quantity = VALUES(required_quantity),
            priority = VALUES(priority),
            quality_requirement = VALUES(quality_requirement),
            order_status = VALUES(order_status)
    """
    try:
        cursor.executemany(query, orders)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def insert_production_records(records):
    """Insert a batch of production records."""
    if not records:
        return
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT IGNORE INTO production_records (
            production_id, machine_id, order_id, part_id,
            product_name, production_quantity, production_timestamp, production_status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        cursor.executemany(query, records)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def insert_quality_inspections(inspections):
    """Insert a batch of quality inspection records."""
    if not inspections:
        return
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT IGNORE INTO quality_inspections (
            inspection_id, part_id, machine_id, order_id,
            dimensional_accuracy, surface_quality, weight,
            inspection_result, defect_category, inspection_timestamp
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        cursor.executemany(query, inspections)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def insert_anomaly(anomaly):
    """
    Insert a single anomaly record into MySQL.
    Skips duplicate unresolved alerts for the same machine and sensor_type
    within the last 2 minutes to prevent alert flooding.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        check_query = """
            SELECT COUNT(*) FROM anomalies
            WHERE machine_id = %s
              AND sensor_type = %s
              AND alert_status = 'Unresolved'
              AND detection_timestamp >= DATE_SUB(%s, INTERVAL 2 MINUTE)
        """
        cursor.execute(
            check_query,
            (anomaly["machine_id"], anomaly["sensor_type"], anomaly["detection_timestamp"]),
        )
        exists = cursor.fetchone()[0]
        if exists > 0:
            return False

        insert_query = """
            INSERT INTO anomalies (
                anomaly_id, machine_id, sensor_type, observed_value,
                normal_range, severity, possible_cause, recommended_action,
                detection_timestamp, alert_status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(
            insert_query,
            (
                anomaly["anomaly_id"],
                anomaly["machine_id"],
                anomaly["sensor_type"],
                anomaly["observed_value"],
                anomaly["normal_range"],
                anomaly["severity"],
                anomaly["possible_cause"],
                anomaly["recommended_action"],
                anomaly["detection_timestamp"],
                anomaly.get("alert_status", "Unresolved"),
            ),
        )
        conn.commit()
        return True
    finally:
        cursor.close()
        conn.close()


def insert_anomalies_batch(anomalies_list):
    """Insert a list of anomalies, skipping duplicates."""
    inserted = 0
    for item in anomalies_list:
        if insert_anomaly(item):
            inserted += 1
    return inserted


def update_machine_status(machine_id, status):
    """Update the operating_status of a machine ('Normal', 'Warning', 'Critical')."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE machines SET operating_status = %s WHERE machine_id = %s",
            (status, machine_id),
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def resolve_anomaly(anomaly_id):
    """Mark an anomaly alert as Resolved in MySQL."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE anomalies SET alert_status = 'Resolved' WHERE anomaly_id = %s",
            (anomaly_id,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()


def get_machines():
    """Fetch all machines joined with their production line name and production count."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT
                m.machine_id,
                m.machine_name,
                m.production_line,
                pl.line_name,
                m.machine_type,
                m.operating_status,
                DATE_FORMAT(m.installation_date, '%Y-%m-%d') AS installation_date,
                COALESCE(p.total_produced, 0) AS total_produced
            FROM machines m
            JOIN production_lines pl ON m.production_line = pl.line_id
            LEFT JOIN (
                SELECT machine_id, SUM(production_quantity) AS total_produced
                FROM production_records
                GROUP BY machine_id
            ) p ON m.machine_id = p.machine_id
            ORDER BY m.machine_id
        """
        cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def get_customer_orders():
    """Fetch all customer orders with customer names."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT
                co.order_id,
                co.customer_id,
                c.customer_name,
                co.product_name,
                co.required_quantity,
                co.priority,
                co.quality_requirement,
                DATE_FORMAT(co.order_date, '%Y-%m-%d') AS order_date,
                DATE_FORMAT(co.delivery_date, '%Y-%m-%d') AS delivery_date,
                co.order_status
            FROM customer_orders co
            JOIN customers c ON co.customer_id = c.customer_id
            ORDER BY co.order_id
        """
        cursor.execute(query)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def get_dashboard_summary():
    """Calculate overall KPIs and chart datasets from MySQL tables."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. Production & quality KPIs
        cursor.execute("""
            SELECT
                COUNT(*) AS total_production,
                SUM(CASE WHEN q.inspection_result = 'PASS' THEN 1 ELSE 0 END) AS good_parts,
                SUM(CASE WHEN q.inspection_result = 'FAIL' THEN 1 ELSE 0 END) AS defective_parts
            FROM production_records p
            LEFT JOIN quality_inspections q ON p.part_id = q.part_id
        """)
        prod_stats = cursor.fetchone() or {}
        total_prod = int(prod_stats.get("total_production") or 0)
        good_parts = int(prod_stats.get("good_parts") or 0)
        defective_parts = int(prod_stats.get("defective_parts") or 0)
        pass_rate = round((good_parts * 100.0 / total_prod), 2) if total_prod > 0 else 0.0

        # 2. Machine count & active anomalies
        cursor.execute("SELECT COUNT(*) AS total_machines FROM machines")
        total_machines = int(cursor.fetchone()["total_machines"])

        cursor.execute("SELECT COUNT(*) AS active_anomalies FROM anomalies WHERE alert_status = 'Unresolved'")
        active_anomalies = int(cursor.fetchone()["active_anomalies"])

        # 3. Production over time (hourly buckets)
        cursor.execute("""
            SELECT
                DATE_FORMAT(production_timestamp, '%H:00') AS hour_label,
                MIN(production_timestamp) AS sort_ts,
                COUNT(*) AS count
            FROM production_records
            GROUP BY hour_label
            ORDER BY sort_ts ASC
        """)
        prod_over_time = [
            {"label": row["hour_label"], "count": int(row["count"])}
            for row in cursor.fetchall()
        ]

        # 4. Machine-wise production & defect percentage
        cursor.execute("""
            SELECT
                m.machine_id,
                m.machine_name,
                COUNT(p.production_id) AS total_production,
                SUM(CASE WHEN q.inspection_result = 'FAIL' THEN 1 ELSE 0 END) AS defective_parts
            FROM machines m
            LEFT JOIN production_records p ON m.machine_id = p.machine_id
            LEFT JOIN quality_inspections q ON p.part_id = q.part_id
            GROUP BY m.machine_id, m.machine_name
            ORDER BY m.machine_id
        """)
        machine_stats = []
        for row in cursor.fetchall():
            tot = int(row["total_production"] or 0)
            defect = int(row["defective_parts"] or 0)
            defect_pct = round((defect * 100.0 / tot), 2) if tot > 0 else 0.0
            machine_stats.append({
                "machine_id": row["machine_id"],
                "machine_name": row["machine_name"],
                "total_production": tot,
                "defective_parts": defect,
                "defect_percentage": defect_pct,
            })

        return {
            "kpis": {
                "total_production": total_prod,
                "good_parts": good_parts,
                "defective_parts": defective_parts,
                "quality_pass_rate": pass_rate,
                "total_machines": total_machines,
                "active_anomalies": active_anomalies,
            },
            "production_over_time": prod_over_time,
            "machine_stats": machine_stats,
        }
    finally:
        cursor.close()
        conn.close()


def get_production_analytics(days=1):
    """Fetch production analytics filtered by last N days (1, 7, or 30)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        time_filter = "WHERE p.production_timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)"

        cursor.execute(
            f"""
            SELECT
                COUNT(p.production_id) AS total_production,
                SUM(CASE WHEN q.inspection_result = 'PASS' THEN 1 ELSE 0 END) AS good_production,
                SUM(CASE WHEN q.inspection_result = 'FAIL' THEN 1 ELSE 0 END) AS rejected_production
            FROM production_records p
            LEFT JOIN quality_inspections q ON p.part_id = q.part_id
            {time_filter}
            """,
            (days,),
        )
        totals = cursor.fetchone() or {}
        total_prod = int(totals.get("total_production") or 0)
        good_prod = int(totals.get("good_production") or 0)
        rejected_prod = int(totals.get("rejected_production") or 0)
        rejection_rate = round((rejected_prod * 100.0 / total_prod), 2) if total_prod > 0 else 0.0

        # By machine
        cursor.execute(
            f"""
            SELECT
                m.machine_name,
                COUNT(p.production_id) AS total_production,
                SUM(CASE WHEN q.inspection_result = 'PASS' THEN 1 ELSE 0 END) AS good_production,
                SUM(CASE WHEN q.inspection_result = 'FAIL' THEN 1 ELSE 0 END) AS rejected_production
            FROM production_records p
            JOIN machines m ON p.machine_id = m.machine_id
            LEFT JOIN quality_inspections q ON p.part_id = q.part_id
            {time_filter}
            GROUP BY m.machine_name
            ORDER BY total_production DESC
            """,
            (days,),
        )
        by_machine = [
            {
                "machine_name": r["machine_name"],
                "total_production": int(r["total_production"] or 0),
                "good_production": int(r["good_production"] or 0),
                "rejected_production": int(r["rejected_production"] or 0),
            }
            for r in cursor.fetchall()
        ]

        # By product
        cursor.execute(
            f"""
            SELECT
                p.product_name,
                COUNT(p.production_id) AS total_production,
                SUM(CASE WHEN q.inspection_result = 'PASS' THEN 1 ELSE 0 END) AS good_production,
                SUM(CASE WHEN q.inspection_result = 'FAIL' THEN 1 ELSE 0 END) AS rejected_production
            FROM production_records p
            LEFT JOIN quality_inspections q ON p.part_id = q.part_id
            {time_filter}
            GROUP BY p.product_name
            ORDER BY total_production DESC
            """,
            (days,),
        )
        by_product = [
            {
                "product_name": r["product_name"],
                "total_production": int(r["total_production"] or 0),
                "good_production": int(r["good_production"] or 0),
                "rejected_production": int(r["rejected_production"] or 0),
            }
            for r in cursor.fetchall()
        ]

        # By production line
        cursor.execute(
            f"""
            SELECT
                pl.line_name,
                COUNT(p.production_id) AS total_production,
                SUM(CASE WHEN q.inspection_result = 'PASS' THEN 1 ELSE 0 END) AS good_production,
                SUM(CASE WHEN q.inspection_result = 'FAIL' THEN 1 ELSE 0 END) AS rejected_production
            FROM production_records p
            JOIN machines m ON p.machine_id = m.machine_id
            JOIN production_lines pl ON m.production_line = pl.line_id
            LEFT JOIN quality_inspections q ON p.part_id = q.part_id
            {time_filter}
            GROUP BY pl.line_name
            ORDER BY total_production DESC
            """,
            (days,),
        )
        by_line = [
            {
                "line_name": r["line_name"],
                "total_production": int(r["total_production"] or 0),
                "good_production": int(r["good_production"] or 0),
                "rejected_production": int(r["rejected_production"] or 0),
            }
            for r in cursor.fetchall()
        ]

        # Recent production records
        cursor.execute(
            f"""
            SELECT
                p.production_id,
                p.machine_id,
                m.machine_name,
                p.order_id,
                p.part_id,
                p.product_name,
                p.production_quantity,
                DATE_FORMAT(p.production_timestamp, '%Y-%m-%d %H:%i:%s') AS production_timestamp,
                p.production_status
            FROM production_records p
            JOIN machines m ON p.machine_id = m.machine_id
            {time_filter}
            ORDER BY p.production_timestamp DESC
            LIMIT 100
            """,
            (days,),
        )
        recent_records = cursor.fetchall()

        return {
            "summary": {
                "total_production": total_prod,
                "good_production": good_prod,
                "rejected_production": rejected_prod,
                "rejection_rate": rejection_rate,
            },
            "by_machine": by_machine,
            "by_product": by_product,
            "by_line": by_line,
            "records": recent_records,
        }
    finally:
        cursor.close()
        conn.close()


def get_quality_inspections(machine_id=None, product=None, result=None, defect=None, search=None, limit=200):
    """Fetch quality inspection records and summary metrics with optional filters."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Overall metrics (unfiltered so KPI cards stay accurate)
        cursor.execute("""
            SELECT
                COUNT(*) AS total_inspected,
                SUM(CASE WHEN inspection_result = 'PASS' THEN 1 ELSE 0 END) AS passed_parts,
                SUM(CASE WHEN inspection_result = 'FAIL' THEN 1 ELSE 0 END) AS failed_parts
            FROM quality_inspections
        """)
        counts = cursor.fetchone() or {}
        total_insp = int(counts.get("total_inspected") or 0)
        passed = int(counts.get("passed_parts") or 0)
        failed = int(counts.get("failed_parts") or 0)
        pass_pct = round((passed * 100.0 / total_insp), 2) if total_insp > 0 else 0.0

        # Defect category counts
        cursor.execute("""
            SELECT defect_category, COUNT(*) AS count
            FROM quality_inspections
            WHERE inspection_result = 'FAIL' AND defect_category IS NOT NULL
            GROUP BY defect_category
            ORDER BY count DESC
        """)
        defect_breakdown = [
            {"defect_category": r["defect_category"], "count": int(r["count"])}
            for r in cursor.fetchall()
        ]

        # Machine-wise rejection percentage
        cursor.execute("""
            SELECT
                m.machine_id,
                m.machine_name,
                COUNT(q.inspection_id) AS total_inspected,
                SUM(CASE WHEN q.inspection_result = 'FAIL' THEN 1 ELSE 0 END) AS failed_parts
            FROM machines m
            LEFT JOIN quality_inspections q ON m.machine_id = q.machine_id
            GROUP BY m.machine_id, m.machine_name
            ORDER BY m.machine_id
        """)
        machine_rejection = []
        for r in cursor.fetchall():
            tot = int(r["total_inspected"] or 0)
            fail = int(r["failed_parts"] or 0)
            rej_pct = round((fail * 100.0 / tot), 2) if tot > 0 else 0.0
            machine_rejection.append({
                "machine_id": r["machine_id"],
                "machine_name": r["machine_name"],
                "total_inspected": tot,
                "failed_parts": fail,
                "rejection_percentage": rej_pct,
            })

        # Filtered records query
        where_clauses = []
        params = []
        if machine_id:
            where_clauses.append("q.machine_id = %s")
            params.append(machine_id)
        if product:
            where_clauses.append("co.product_name = %s")
            params.append(product)
        if result:
            where_clauses.append("q.inspection_result = %s")
            params.append(result)
        if defect:
            where_clauses.append("q.defect_category = %s")
            params.append(defect)
        if search:
            where_clauses.append("(q.part_id LIKE %s OR q.order_id LIKE %s OR co.product_name LIKE %s)")
            like = f"%{search}%"
            params.extend([like, like, like])

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        params.append(limit)

        cursor.execute(
            f"""
            SELECT
                q.inspection_id,
                q.part_id,
                q.machine_id,
                m.machine_name,
                q.order_id,
                co.product_name,
                co.quality_requirement,
                CAST(q.dimensional_accuracy AS FLOAT) AS dimensional_accuracy,
                q.surface_quality,
                CAST(q.weight AS FLOAT) AS weight,
                q.inspection_result,
                COALESCE(q.defect_category, 'None') AS defect_category,
                DATE_FORMAT(q.inspection_timestamp, '%Y-%m-%d %H:%i:%s') AS inspection_timestamp
            FROM quality_inspections q
            JOIN machines m ON q.machine_id = m.machine_id
            JOIN customer_orders co ON q.order_id = co.order_id
            {where_sql}
            ORDER BY q.inspection_timestamp DESC
            LIMIT %s
            """,
            tuple(params),
        )
        records = cursor.fetchall()

        return {
            "summary": {
                "total_inspected": total_insp,
                "passed_parts": passed,
                "failed_parts": failed,
                "pass_percentage": pass_pct,
            },
            "defect_breakdown": defect_breakdown,
            "machine_rejection": machine_rejection,
            "records": records,
        }
    finally:
        cursor.close()
        conn.close()


def get_anomalies(machine_id=None, sensor_type=None, severity=None, alert_status=None, limit=200):
    """Fetch detected anomalies with optional filters."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        where_clauses = []
        params = []
        if machine_id:
            where_clauses.append("a.machine_id = %s")
            params.append(machine_id)
        if sensor_type:
            where_clauses.append("a.sensor_type = %s")
            params.append(sensor_type)
        if severity:
            where_clauses.append("a.severity = %s")
            params.append(severity)
        if alert_status:
            where_clauses.append("a.alert_status = %s")
            params.append(alert_status)

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        params.append(limit)

        cursor.execute(
            f"""
            SELECT
                a.anomaly_id,
                a.machine_id,
                m.machine_name,
                a.sensor_type,
                CAST(a.observed_value AS FLOAT) AS observed_value,
                a.normal_range,
                a.severity,
                a.possible_cause,
                a.recommended_action,
                DATE_FORMAT(a.detection_timestamp, '%Y-%m-%d %H:%i:%s') AS detection_timestamp,
                a.alert_status
            FROM anomalies a
            JOIN machines m ON a.machine_id = m.machine_id
            {where_sql}
            ORDER BY a.detection_timestamp DESC
            LIMIT %s
            """,
            tuple(params),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def get_next_sequence_numbers():
    """Return current counts of production and inspection records to avoid ID collisions."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM production_records")
        prod_count = int(cursor.fetchone()[0])
        cursor.execute("SELECT COUNT(*) FROM quality_inspections")
        insp_count = int(cursor.fetchone()[0])
        return prod_count, insp_count
    finally:
        cursor.close()
        conn.close()


def test_mysql_connection():
    """Return True if MySQL is reachable and smart_manufacturing exists."""
    try:
        conn = get_connection()
        conn.close()
        return True
    except Error:
        return False

