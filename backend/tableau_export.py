"""
Tableau CSV Export Utility.

Exports the MySQL `production_quality_summary` view and core quality/anomaly
tables to CSV files in the `exports/` directory so they can be imported into
Tableau Desktop or Tableau Public if direct MySQL connection is unavailable.

Usage:
    python3 backend/tableau_export.py
"""

import csv
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend import mysql_db

EXPORTS_DIR = os.path.join(PROJECT_ROOT, "exports")


def export_query_to_csv(query, filename):
    """Run a SQL SELECT query and write the results to exports/<filename>."""
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    filepath = os.path.join(EXPORTS_DIR, filename)

    conn = mysql_db.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        headers = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

        print(f"[Tableau Export] Wrote {len(rows)} rows -> {filepath}")
        return filepath
    finally:
        cursor.close()
        conn.close()


def export_all_tableau_datasets():
    """Export all datasets needed for the 3 Tableau dashboards."""
    files = []

    # 1. Production Quality Summary View (Dashboard 1 & 2)
    files.append(
        export_query_to_csv(
            "SELECT * FROM production_quality_summary ORDER BY production_date DESC",
            "production_quality_summary.csv",
        )
    )

    # 2. Detailed Quality Inspections (Dashboard 2: Defect categories & rejection)
    files.append(
        export_query_to_csv(
            """
            SELECT
                q.inspection_id,
                q.part_id,
                m.machine_name,
                pl.line_name AS production_line,
                co.product_name,
                q.dimensional_accuracy,
                q.surface_quality,
                q.weight,
                q.inspection_result,
                COALESCE(q.defect_category, 'None') AS defect_category,
                q.inspection_timestamp
            FROM quality_inspections q
            JOIN machines m ON q.machine_id = m.machine_id
            JOIN production_lines pl ON m.production_line = pl.line_id
            JOIN customer_orders co ON q.order_id = co.order_id
            ORDER BY q.inspection_timestamp DESC
            """,
            "quality_inspections_export.csv",
        )
    )

    # 3. Machine Anomalies (Dashboard 3: Machine Performance & Anomaly Counts)
    files.append(
        export_query_to_csv(
            """
            SELECT
                a.anomaly_id,
                m.machine_id,
                m.machine_name,
                pl.line_name AS production_line,
                a.sensor_type,
                a.observed_value,
                a.normal_range,
                a.severity,
                a.possible_cause,
                a.detection_timestamp,
                a.alert_status
            FROM anomalies a
            JOIN machines m ON a.machine_id = m.machine_id
            JOIN production_lines pl ON m.production_line = pl.line_id
            ORDER BY a.detection_timestamp DESC
            """,
            "anomalies_export.csv",
        )
    )

    return files


if __name__ == "__main__":
    export_all_tableau_datasets()

