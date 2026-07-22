"""
Sensor Simulator - Fog-Based Industrial Machine Fault Detection
---------------------------------------------------------------
Reads rows from the CSV dataset and simulates sensor readings
being sent from industrial machines to the fog node.

This represents the Edge/Sensor Layer in the fog architecture.
"""

import argparse
import csv
import time
import requests
import os
import sys

# Default path to the dataset
DATA_FILE = os.path.join(
    os.path.dirname(__file__),
    '..',
    'data',
    'industrial_fault_detection_data_1000.csv'
)

# A fixed machine ID to simulate one machine in this demo
MACHINE_ID = "MACHINE-001"


def load_dataset(filepath):
    """Load sensor readings from the CSV file."""
    if not os.path.exists(filepath):
        print(f"[ERROR] Dataset not found at: {filepath}")
        print("Please ensure the CSV file is at: data/industrial_fault_detection_data_1000.csv")
        sys.exit(1)

    readings = []

    try:
        with open(filepath, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                readings.append(row)
    except Exception as e:
        print(f"[ERROR] Could not read dataset: {e}")
        sys.exit(1)

    print(f"[INFO] Loaded {len(readings)} readings from dataset.")
    return readings


def build_payload(row, machine_id):
    """Build a sensor reading payload from a CSV row."""
    try:
        payload = {
            "machine_id": machine_id,
            "timestamp": row["Timestamp"],
            "vibration": float(row["Vibration (mm/s)"]),
            "temperature": float(row["Temperature (°C)"]),
            "pressure": float(row["Pressure (bar)"]),
            "fault_label": int(row["Fault Label"])
        }
        return payload

    except KeyError as e:
        print(f"[ERROR] Missing expected column in dataset: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"[ERROR] Invalid numeric value in dataset: {e}")
        sys.exit(1)


def send_reading(payload, fog_url, index, total):
    """Send a single reading to the fog node and print the result."""
    print(f"[SENSOR] Sending reading {index}/{total} to fog node...")

    try:
        response = requests.post(fog_url, json=payload, timeout=5)

        if response.status_code == 200:
            try:
                data = response.json()
                status = data.get("status", "accepted")
                machine_status = data.get("machine_status", "unknown")
                print(f"  Fog response: {status} | Machine status: {machine_status}")
            except ValueError:
                print("  [WARNING] Fog node responded, but response was not JSON.")
        else:
            print(f"  [WARNING] Fog node returned status code: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print(f"  [WARNING] Could not reach fog node at {fog_url}. Is it running?")
    except requests.exceptions.Timeout:
        print("  [WARNING] Fog node request timed out.")
    except Exception as e:
        print(f"  [ERROR] Unexpected error: {e}")


def run_simulator(args):
    """Main loop: load dataset and send readings to the fog node."""
    if args.count <= 0:
        print("[ERROR] --count must be greater than 0.")
        sys.exit(1)

    readings = load_dataset(DATA_FILE)

    selected = readings[:args.count]
    total = len(selected)

    if total == 0:
        print("[ERROR] No readings available to send.")
        sys.exit(1)

    print("\n[SENSOR] Starting industrial machine sensor simulator")
    print(f"  Machine ID       : {MACHINE_ID}")
    print(f"  Target fog node  : {args.fog_url}")
    print(f"  Readings to send : {total}")
    print(f"  Generate interval: {args.generate_interval}s")
    print(f"  Dispatch interval: {args.dispatch_interval}s")
    print("-" * 60)

    for i, row in enumerate(selected, start=1):
        payload = build_payload(row, MACHINE_ID)

        # Simulate sensor reading generation delay
        time.sleep(args.generate_interval)

        send_reading(payload, args.fog_url, i, total)

        # Simulate dispatch delay between two readings
        if i < total:
            time.sleep(args.dispatch_interval)

    print("\n[SENSOR] All readings sent. Simulator finished.")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Industrial Machine Sensor Simulator"
    )

    parser.add_argument(
        '--count',
        type=int,
        default=50,
        help='Number of readings to send (default: 50)'
    )

    parser.add_argument(
        '--generate-interval',
        type=float,
        default=0.5,
        help='Seconds to wait before generating each reading (default: 0.5)'
    )

    parser.add_argument(
        '--dispatch-interval',
        type=float,
        default=1.0,
        help='Seconds to wait after sending each reading (default: 1.0)'
    )

    parser.add_argument(
        '--fog-url',
        type=str,
        default='http://localhost:7000/ingest',
        help='URL of the fog node ingest endpoint'
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_simulator(args)