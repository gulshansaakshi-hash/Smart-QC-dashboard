"""
Flask Backend Application for the Smart Manufacturing Quality Control
& Anomaly Detection System.

Connects the HTML/JS frontend to MySQL, Apache Cassandra, Apache Kafka,
and the Python data generation, anomaly detection, and root cause modules.
"""

import os
import sys
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import FLASK_CONFIG
from backend import mysql_db, cassandra_db, data_generator
from backend.anomaly_detection import analyze_sensor_reading, determine_machine_status
from backend import kafka_producer, kafka_consumer

FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")


def _populate_initial_dataset():
    """Clear existing demo data and populate fresh initial records in MySQL & Cassandra."""
    mysql_db.init_database()
    cassandra_db.init_cassandra_schema()

    mysql_db.clear_all_data()
    machine_ids = [m[0] for m in data_generator.MACHINES]
    cassandra_db.clear_sensor_readings(machine_ids)

    dataset = data_generator.generate_initial_dataset()

    mysql_db.insert_production_lines(dataset["production_lines"])
    mysql_db.insert_machines(dataset["machines"])
    mysql_db.insert_customers(dataset["customers"])
    mysql_db.insert_customer_orders(dataset["orders"])
    mysql_db.insert_production_records(dataset["production_records"])
    mysql_db.insert_quality_inspections(dataset["quality_inspections"])

    # Store all 1,050+ sensor readings in Cassandra
    sensor_readings = dataset["sensor_readings"]
    cassandra_db.insert_sensor_readings_batch(sensor_readings)

    # Analyze sensor readings per machine using a rolling history window
    by_machine = {mid: [] for mid in machine_ids}
    for reading in sensor_readings:
        by_machine[reading["machine_id"]].append(reading)

    detected_anomalies = []
    for mid, readings in by_machine.items():
        latest_anomalies = []
        for idx, reading in enumerate(readings):
            window = readings[max(0, idx - 30):idx]
            found = analyze_sensor_reading(reading, history_readings=window)
            detected_anomalies.extend(found)
            if idx == len(readings) - 1:
                latest_anomalies = found

        mysql_db.update_machine_status(mid, determine_machine_status(latest_anomalies))

    inserted_anomalies = mysql_db.insert_anomalies_batch(detected_anomalies)
    return {
        "machines": len(dataset["machines"]),
        "orders": len(dataset["orders"]),
        "production_records": len(dataset["production_records"]),
        "quality_inspections": len(dataset["quality_inspections"]),
        "sensor_readings": len(sensor_readings),
        "anomalies_detected": inserted_anomalies,
    }


def _generate_incremental_data():
    """Generate a new batch of production, quality, and sensor readings."""
    orders_dicts = mysql_db.get_customer_orders()
    if not orders_dicts:
        return _populate_initial_dataset()

    orders_tuples = [
        (
            o["order_id"], o["customer_id"], o["product_name"],
            o["required_quantity"], o["priority"], o["quality_requirement"],
            o["order_date"], o["delivery_date"], o["order_status"],
        )
        for o in orders_dicts
    ]

    prod_count, insp_count = mysql_db.get_next_sequence_numbers()
    start_idx = max(prod_count, insp_count) + 1
    now = datetime.now()

    prod_rows, insp_rows = data_generator.generate_production_and_quality_records(
        orders_tuples, count=15, start_index=start_idx, hours_back=1, base_time=now
    )
    mysql_db.insert_production_records(prod_rows)
    mysql_db.insert_quality_inspections(insp_rows)

    new_anomalies_count = 0
    for machine in data_generator.MACHINES:
        mid = machine[0]
        reading = data_generator.generate_single_sensor_reading(mid, timestamp=now)
        cassandra_db.insert_sensor_reading(reading)
        history = cassandra_db.get_sensor_history(mid, limit=30)
        found = analyze_sensor_reading(reading, history_readings=history)
        mysql_db.update_machine_status(mid, determine_machine_status(found))
        new_anomalies_count += mysql_db.insert_anomalies_batch(found)

    return {
        "new_production_records": len(prod_rows),
        "new_quality_inspections": len(insp_rows),
        "new_sensor_readings": len(data_generator.MACHINES),
        "new_anomalies": new_anomalies_count,
    }


# ----------------------------------------------------------------------------
# Frontend Route
# ----------------------------------------------------------------------------
@app.route("/")
def serve_dashboard():
    """Serve the main HTML dashboard."""
    return send_from_directory(FRONTEND_DIR, "index.html")


# ----------------------------------------------------------------------------
# REST API Endpoints
# ----------------------------------------------------------------------------
@app.route("/api/dashboard", methods=["GET"])
def api_dashboard():
    """Return KPIs, chart datasets, latest 5 alerts, and machine overview."""
    try:
        summary = mysql_db.get_dashboard_summary()
        machines = mysql_db.get_machines()
        machine_ids = [m["machine_id"] for m in machines]

        latest_sensors = cassandra_db.get_latest_readings_all_machines(machine_ids)
        for m in machines:
            m["latest_sensor"] = latest_sensors.get(m["machine_id"])

        recent_alerts = mysql_db.get_anomalies(limit=5)

        # Build temperature & vibration trend arrays across machines (last 20 readings of M001..M005)
        sensor_trends = {}
        for mid in machine_ids:
            hist = cassandra_db.get_sensor_history(mid, limit=15)
            sensor_trends[mid] = list(reversed(hist))

        return jsonify({
            "status": "ok",
            "kpis": summary["kpis"],
            "production_over_time": summary["production_over_time"],
            "machine_stats": summary["machine_stats"],
            "machines": machines,
            "recent_alerts": recent_alerts,
            "sensor_trends": sensor_trends,
            "simulation_running": kafka_producer.is_producer_running(),
        })
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/machines", methods=["GET"])
def api_machines():
    """Return all machines with latest sensor readings, or details for one machine."""
    try:
        machine_id = request.args.get("machine_id")
        machines = mysql_db.get_machines()

        if machine_id:
            machine = next((m for m in machines if m["machine_id"] == machine_id), None)
            if not machine:
                return jsonify({"status": "error", "message": "Machine not found"}), 404

            history = cassandra_db.get_sensor_history(machine_id, limit=30)
            anomalies = mysql_db.get_anomalies(machine_id=machine_id, limit=20)
            return jsonify({
                "status": "ok",
                "machine": machine,
                "latest_sensor": history[0] if history else None,
                "sensor_history": list(reversed(history)),
                "anomalies": anomalies,
            })

        machine_ids = [m["machine_id"] for m in machines]
        latest_sensors = cassandra_db.get_latest_readings_all_machines(machine_ids)
        for m in machines:
            m["latest_sensor"] = latest_sensors.get(m["machine_id"])

        return jsonify({"status": "ok", "machines": machines})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/sensors", methods=["GET"])
def api_sensors():
    """Return latest sensor readings for all machines or history for one machine."""
    try:
        machine_id = request.args.get("machine_id")
        limit = int(request.args.get("limit", 50))

        if machine_id:
            history = cassandra_db.get_sensor_history(machine_id, limit=limit)
            return jsonify({"status": "ok", "machine_id": machine_id, "readings": history})

        machines = mysql_db.get_machines()
        machine_ids = [m["machine_id"] for m in machines]
        latest = cassandra_db.get_latest_readings_all_machines(machine_ids)
        return jsonify({"status": "ok", "latest_readings": latest})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/production", methods=["GET"])
def api_production():
    """Return production analytics and records filtered by 1, 7, or 30 days."""
    try:
        days = int(request.args.get("days", 1))
        if days not in (1, 7, 30):
            days = 1
        data = mysql_db.get_production_analytics(days=days)
        return jsonify({"status": "ok", "days": days, **data})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/quality", methods=["GET"])
def api_quality():
    """Return quality inspection summary, defect breakdown, and filtered records."""
    try:
        machine_id = request.args.get("machine_id") or None
        product = request.args.get("product") or None
        result = request.args.get("result") or None
        defect = request.args.get("defect") or None
        search = request.args.get("search") or None

        data = mysql_db.get_quality_inspections(
            machine_id=machine_id,
            product=product,
            result=result,
            defect=defect,
            search=search,
        )
        return jsonify({"status": "ok", **data})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/anomalies", methods=["GET"])
def api_anomalies():
    """Return detected anomalies with optional filters."""
    try:
        machine_id = request.args.get("machine_id") or None
        sensor_type = request.args.get("sensor_type") or None
        severity = request.args.get("severity") or None
        alert_status = request.args.get("alert_status") or None

        records = mysql_db.get_anomalies(
            machine_id=machine_id,
            sensor_type=sensor_type,
            severity=severity,
            alert_status=alert_status,
        )
        return jsonify({"status": "ok", "anomalies": records})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/root-causes", methods=["GET"])
def api_root_causes():
    """Return anomalies enriched with supporting latest sensor readings for RCA view."""
    try:
        anomalies = mysql_db.get_anomalies(limit=50)
        machines = mysql_db.get_machines()
        machine_ids = [m["machine_id"] for m in machines]
        latest_sensors = cassandra_db.get_latest_readings_all_machines(machine_ids)

        results = []
        for anom in anomalies:
            results.append({
                "anomaly_id": anom["anomaly_id"],
                "machine_id": anom["machine_id"],
                "machine_name": anom["machine_name"],
                "detected_problem": f"{anom['sensor_type']} ({anom['observed_value']}, normal: {anom['normal_range']})",
                "possible_cause": anom["possible_cause"],
                "recommended_action": anom["recommended_action"],
                "severity": anom["severity"],
                "detection_timestamp": anom["detection_timestamp"],
                "alert_status": anom["alert_status"],
                "supporting_sensors": latest_sensors.get(anom["machine_id"], {}),
            })

        return jsonify({
            "status": "ok",
            "note": "Root causes are simulated suggestions for academic demonstration and not confirmed engineering diagnoses.",
            "root_causes": results,
        })
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/generate-data", methods=["POST"])
def api_generate_data():
    """Generate initial data, incremental new data, or reset demo data."""
    try:
        payload = request.get_json(silent=True) or {}
        action = payload.get("action", "new")

        if action in ("initial", "reset"):
            stats = _populate_initial_dataset()
            msg = "Initial demo data generated." if action == "initial" else "Demo data reset successfully."
            return jsonify({"status": "ok", "message": msg, "stats": stats})

        stats = _generate_incremental_data()
        return jsonify({"status": "ok", "message": "New manufacturing & sensor data generated.", "stats": stats})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/start-simulation", methods=["POST"])
def api_start_simulation():
    """Start Kafka consumer and producer threads for live sensor streaming."""
    try:
        if kafka_producer.is_producer_running():
            return jsonify({"status": "ok", "message": "Simulation is already running.", "running": True})

        kafka_consumer.start_consumer()
        kafka_producer.start_producer()
        return jsonify({"status": "ok", "message": "Live Kafka simulation started.", "running": True})
    except Exception as exc:
        return jsonify({
            "status": "error",
            "message": f"Failed to start Kafka simulation. Ensure Kafka & Cassandra are running: {exc}",
            "running": False,
        }), 500


@app.route("/api/stop-simulation", methods=["POST"])
def api_stop_simulation():
    """Stop the Kafka producer and consumer simulation threads."""
    try:
        kafka_producer.stop_producer()
        kafka_consumer.stop_consumer()
        return jsonify({"status": "ok", "message": "Live simulation stopped.", "running": False})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/resolve-alert", methods=["POST"])
def api_resolve_alert():
    """Mark a specific anomaly alert as Resolved in MySQL."""
    try:
        payload = request.get_json(silent=True) or {}
        anomaly_id = payload.get("anomaly_id")
        if not anomaly_id:
            return jsonify({"status": "error", "message": "anomaly_id is required"}), 400

        updated = mysql_db.resolve_anomaly(anomaly_id)
        if not updated:
            return jsonify({"status": "error", "message": "Anomaly not found"}), 404

        return jsonify({"status": "ok", "message": f"Alert {anomaly_id} marked as Resolved."})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


if __name__ == "__main__":
    app.run(
        host=FLASK_CONFIG["host"],
        port=FLASK_CONFIG["port"],
        debug=FLASK_CONFIG["debug"],
        use_reloader=False,
    )

