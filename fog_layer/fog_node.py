"""
Fog Node - Fog-Based Industrial Machine Fault Detection
-------------------------------------------------------
Receives raw sensor readings, applies local processing
(rolling calculations, anomaly detection, status classification)
and forwards enriched data to the cloud backend.

This represents the Fog Layer in the fog computing architecture.
The fog node sits between the sensor layer and the cloud backend.
It performs quick local processing before sending useful data to the backend.
"""

from flask import Flask, request, jsonify
from collections import deque
import requests
import csv
import os
import math
from datetime import datetime

app = Flask(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

FOG_PORT = 7000
BACKEND_URL = "https://swx9zp4ye8.execute-api.us-east-1.amazonaws.com/readings"

FOG_OUTPUT_FILE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "fog_processed_readings.csv"
)

# Rolling window size for fog-level calculations
WINDOW_SIZE = 10

# Thresholds for rule-based anomaly detection
VIBRATION_THRESHOLD = 0.75      # mm/s
TEMPERATURE_THRESHOLD = 110.0   # °C
PRESSURE_THRESHOLD = 9.5        # bar

# ── In-memory rolling buffers ──────────────────────────────────────────────────

vibration_buffer = deque(maxlen=WINDOW_SIZE)
temperature_buffer = deque(maxlen=WINDOW_SIZE)

# ── CSV output setup ───────────────────────────────────────────────────────────

CSV_HEADERS = [
    "timestamp",
    "machine_id",
    "vibration",
    "temperature",
    "pressure",
    "rolling_rms_vibration",
    "rolling_mean_temperature",
    "vibration_flag",
    "temperature_flag",
    "pressure_flag",
    "machine_status",
    "alert_message",
    "fault_label"
]


def init_output_file():
    """Create fog output CSV file with headers if it does not already exist."""
    os.makedirs(os.path.dirname(FOG_OUTPUT_FILE), exist_ok=True)

    if not os.path.exists(FOG_OUTPUT_FILE):
        with open(FOG_OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()


# ── Validation function ────────────────────────────────────────────────────────

def validate_payload(payload):
    """
    Validate incoming sensor payload before processing.
    This prevents the fog node from crashing if any field is missing or invalid.
    """
    required_fields = [
        "machine_id",
        "timestamp",
        "vibration",
        "temperature",
        "pressure",
        "fault_label"
    ]

    for field in required_fields:
        if field not in payload:
            return False, f"Missing required field: {field}"

    try:
        payload["vibration"] = float(payload["vibration"])
        payload["temperature"] = float(payload["temperature"])
        payload["pressure"] = float(payload["pressure"])
        payload["fault_label"] = int(payload["fault_label"])
    except (ValueError, TypeError):
        return False, "Sensor values must be numeric."

    return True, payload


# ── Fog processing functions ───────────────────────────────────────────────────

def calculate_rolling_rms(values):
    """
    Calculate Root Mean Square of vibration values.
    RMS is useful because it gives a better indication of vibration severity
    over a recent time window.
    """
    if not values:
        return 0.0

    mean_square = sum(v ** 2 for v in values) / len(values)
    rms_value = math.sqrt(mean_square)

    return round(rms_value, 4)


def calculate_rolling_mean(values):
    """Calculate rolling average temperature using recent readings."""
    if not values:
        return 0.0

    mean_value = sum(values) / len(values)

    return round(mean_value, 4)


def detect_anomalies(vibration, temperature, pressure):
    """
    Apply simple threshold rules to detect abnormal sensor values.
    This keeps the project easy to understand and suitable for a fog layer demo.
    """
    return {
        "vibration_flag": vibration >= VIBRATION_THRESHOLD,
        "temperature_flag": temperature >= TEMPERATURE_THRESHOLD,
        "pressure_flag": pressure >= PRESSURE_THRESHOLD
    }


def classify_status(flags):
    """
    Classify machine health based on number of abnormal sensor values.

    0 abnormal values  -> Normal
    1 abnormal value   -> Warning
    2 or more abnormal -> Critical
    """
    active_flags = sum(flags.values())

    if active_flags >= 2:
        return "Critical"
    elif active_flags == 1:
        return "Warning"
    else:
        return "Normal"


def build_alert_message(flags, status):
    """Create a simple readable alert message for dashboard and logs."""
    if status == "Normal":
        return "All systems operating normally."

    issues = []

    if flags["vibration_flag"]:
        issues.append(f"High vibration detected >= {VIBRATION_THRESHOLD} mm/s")

    if flags["temperature_flag"]:
        issues.append(f"Overheating detected >= {TEMPERATURE_THRESHOLD} °C")

    if flags["pressure_flag"]:
        issues.append(f"High pressure detected >= {PRESSURE_THRESHOLD} bar")

    return f"{status} alert: " + "; ".join(issues)


def process_reading(payload):
    """
    Main fog processing logic.

    Steps:
    1. Read vibration, temperature and pressure values.
    2. Update rolling buffers.
    3. Calculate rolling RMS vibration and rolling mean temperature.
    4. Detect sensor anomalies using threshold rules.
    5. Classify the machine status.
    6. Create an alert message.
    """
    vibration = payload["vibration"]
    temperature = payload["temperature"]
    pressure = payload["pressure"]

    # Update local fog buffers
    vibration_buffer.append(vibration)
    temperature_buffer.append(temperature)

    # Fog-level feature calculation
    rolling_rms_vibration = calculate_rolling_rms(list(vibration_buffer))
    rolling_mean_temperature = calculate_rolling_mean(list(temperature_buffer))

    # Rule-based anomaly detection
    flags = detect_anomalies(vibration, temperature, pressure)

    # Overall machine status
    machine_status = classify_status(flags)

    # Human-readable alert message
    alert_message = build_alert_message(flags, machine_status)

    processed_reading = {
        "timestamp": payload.get("timestamp", datetime.now().isoformat()),
        "machine_id": payload.get("machine_id", "UNKNOWN"),
        "vibration": round(vibration, 4),
        "temperature": round(temperature, 4),
        "pressure": round(pressure, 4),
        "rolling_rms_vibration": rolling_rms_vibration,
        "rolling_mean_temperature": rolling_mean_temperature,
        "vibration_flag": flags["vibration_flag"],
        "temperature_flag": flags["temperature_flag"],
        "pressure_flag": flags["pressure_flag"],
        "machine_status": machine_status,
        "alert_message": alert_message,
        "fault_label": payload.get("fault_label", -1)
    }

    return processed_reading


# ── Storage and backend forwarding ─────────────────────────────────────────────

def save_to_csv(processed):
    """Append processed fog reading to local CSV storage."""
    init_output_file()

    with open(FOG_OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writerow({key: processed.get(key, "") for key in CSV_HEADERS})


def forward_to_backend(processed):
    """
    Forward enriched fog data to the backend.

    If the backend is not running, the fog node will still continue.
    This shows that fog processing can continue even if cloud/backend
    connection is temporarily unavailable.
    """
    try:
        response = requests.post(BACKEND_URL, json=processed, timeout=3)

        if 200 <= response.status_code < 300:
            print(f"  [FOG -> BACKEND] Forwarded successfully. Status: {processed['machine_status']}")
        else:
            print(f"  [FOG -> BACKEND] Backend returned status code: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print(f"  [FOG -> BACKEND] WARNING: Backend not reachable at {BACKEND_URL}")
    except requests.exceptions.Timeout:
        print("  [FOG -> BACKEND] WARNING: Backend request timed out.")
    except Exception as e:
        print(f"  [FOG -> BACKEND] ERROR: {e}")


# ── Flask routes ───────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    """Basic information endpoint."""
    return jsonify({
        "service": "Fog Node",
        "project": "Industrial Machine Fault Detection",
        "description": "Receives sensor readings, performs fog processing and forwards data to backend.",
        "port": FOG_PORT,
        "backend_url": BACKEND_URL,
        "endpoints": ["/health", "/ingest"]
    })


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "service": "fog_node",
        "port": FOG_PORT
    })


@app.route("/ingest", methods=["POST"])
def ingest():
    """
    Main ingest endpoint.

    Receives raw readings from the sensor simulator,
    validates the payload, processes it locally,
    saves fog output and forwards enriched data to backend.
    """
    payload = request.get_json(silent=True)

    if not payload:
        return jsonify({
            "status": "error",
            "message": "No JSON payload received."
        }), 400

    is_valid, result = validate_payload(payload)

    if not is_valid:
        return jsonify({
            "status": "error",
            "message": result
        }), 400

    payload = result

    print(f"\n[FOG] Received reading from {payload['machine_id']}")
    print(
        f"  Vibration: {payload['vibration']:.4f} mm/s | "
        f"Temperature: {payload['temperature']:.2f} °C | "
        f"Pressure: {payload['pressure']:.2f} bar"
    )

    # Process at fog level
    processed = process_reading(payload)

    print(f"  -> Machine Status: {processed['machine_status']}")
    print(f"  -> Alert: {processed['alert_message']}")
    print(f"  -> Rolling RMS Vibration: {processed['rolling_rms_vibration']}")
    print(f"  -> Rolling Mean Temperature: {processed['rolling_mean_temperature']}")

    # Save processed reading locally
    save_to_csv(processed)

    # Forward processed reading to backend
    forward_to_backend(processed)

    return jsonify({
        "status": "accepted",
        "machine_status": processed["machine_status"],
        "alert": processed["alert_message"],
        "rolling_rms_vibration": processed["rolling_rms_vibration"],
        "rolling_mean_temperature": processed["rolling_mean_temperature"]
    }), 200


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_output_file()

    print("=" * 65)
    print("  Fog Node - Industrial Machine Fault Detection")
    print("=" * 65)
    print(f"  Listening on port      : {FOG_PORT}")
    print(f"  Backend endpoint       : {BACKEND_URL}")
    print(f"  Local fog output file  : {FOG_OUTPUT_FILE}")
    print(f"  Window size            : {WINDOW_SIZE}")
    print("-" * 65)
    print("  Threshold Rules")
    print(f"  Vibration threshold    : {VIBRATION_THRESHOLD} mm/s")
    print(f"  Temperature threshold  : {TEMPERATURE_THRESHOLD} °C")
    print(f"  Pressure threshold     : {PRESSURE_THRESHOLD} bar")
    print("=" * 65)

    app.run(host="0.0.0.0", port=FOG_PORT, debug=False)