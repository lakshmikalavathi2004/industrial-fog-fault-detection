"""
Cloud Backend - Fog-Based Industrial Machine Fault Detection
------------------------------------------------------------
Receives processed readings from the fog node and stores them.
Exposes a REST API for the Streamlit dashboard.

This represents the Cloud Layer in the fog computing architecture.

Scalability Note:
This local FastAPI backend is used for development and demonstration.
For public cloud deployment, this backend can be replaced with:

- AWS API Gateway   -> managed REST API endpoint
- AWS SQS           -> queue for incoming fog readings
- AWS Lambda        -> serverless processing
- AWS DynamoDB      -> scalable cloud database

This supports the project requirement for a scalable backend and dashboard.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import csv
import os
import pandas as pd

# ── App setup ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Industrial Fault Detection Backend",
    description="Cloud backend API for fog-based industrial machine fault detection",
    version="1.0.0"
)

# Allow the Streamlit dashboard to access the backend API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Storage configuration ──────────────────────────────────────────────────────

BACKEND_PORT = 9000

BACKEND_DATA_FILE = os.path.join(
    os.path.dirname(__file__),
    "..",
    "data",
    "backend_readings.csv"
)

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


# ── Pydantic model ─────────────────────────────────────────────────────────────

class SensorReading(BaseModel):
    """
    Data model for a fog-processed sensor reading.
    The fog node sends this structure to the backend.
    """
    timestamp: str
    machine_id: str
    vibration: float
    temperature: float
    pressure: float
    rolling_rms_vibration: Optional[float] = None
    rolling_mean_temperature: Optional[float] = None
    vibration_flag: Optional[bool] = None
    temperature_flag: Optional[bool] = None
    pressure_flag: Optional[bool] = None
    machine_status: Optional[str] = "Normal"
    alert_message: Optional[str] = ""
    fault_label: Optional[int] = -1


# ── Storage helper functions ───────────────────────────────────────────────────

def init_storage():
    """Create the backend CSV file with headers if it does not exist."""
    os.makedirs(os.path.dirname(BACKEND_DATA_FILE), exist_ok=True)

    if not os.path.exists(BACKEND_DATA_FILE):
        with open(BACKEND_DATA_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()

        print(f"[BACKEND] Created storage file: {BACKEND_DATA_FILE}")


def append_reading(reading: dict):
    """Append one fog-processed reading to backend CSV storage."""
    init_storage()

    with open(BACKEND_DATA_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        row = {key: reading.get(key, "") for key in CSV_HEADERS}
        writer.writerow(row)


def load_readings():
    """Load all readings from the backend CSV file."""
    if not os.path.exists(BACKEND_DATA_FILE):
        return []

    try:
        df = pd.read_csv(BACKEND_DATA_FILE, encoding="utf-8")

        if df.empty:
            return []

        # Replace NaN values with None for clean JSON output
        df = df.where(pd.notnull(df), None)

        return df.to_dict(orient="records")

    except pd.errors.EmptyDataError:
        return []
    except Exception as e:
        print(f"[BACKEND] Error loading readings: {e}")
        return []


def calculate_summary(readings):
    """Calculate dashboard summary statistics from stored readings."""
    if not readings:
        return {
            "total": 0,
            "normal_count": 0,
            "warning_count": 0,
            "critical_count": 0,
            "avg_vibration": 0,
            "avg_temperature": 0,
            "avg_pressure": 0
        }

    df = pd.DataFrame(readings)

    # Convert numeric columns safely
    for col in ["vibration", "temperature", "pressure"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return {
        "total": int(len(df)),
        "normal_count": int((df["machine_status"] == "Normal").sum()),
        "warning_count": int((df["machine_status"] == "Warning").sum()),
        "critical_count": int((df["machine_status"] == "Critical").sum()),
        "avg_vibration": round(float(df["vibration"].mean()), 4) if not df["vibration"].isna().all() else 0,
        "avg_temperature": round(float(df["temperature"].mean()), 4) if not df["temperature"].isna().all() else 0,
        "avg_pressure": round(float(df["pressure"].mean()), 4) if not df["pressure"].isna().all() else 0
    }


# ── Startup event ──────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup():
    """Initialise backend storage when the API starts."""
    init_storage()
    print("=" * 65)
    print("  Cloud Backend - Industrial Machine Fault Detection")
    print("=" * 65)
    print(f"  Backend port       : {BACKEND_PORT}")
    print(f"  Storage file       : {BACKEND_DATA_FILE}")
    print("  Waiting for fog node data...")
    print("=" * 65)


# ── API routes ─────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    """Basic backend information endpoint."""
    return {
        "service": "Industrial Fault Detection Backend",
        "project": "Fog-Based Industrial Machine Fault Detection",
        "description": "Cloud layer that receives fog-processed sensor readings and provides dashboard APIs.",
        "port": BACKEND_PORT,
        "endpoints": [
            "/health",
            "/readings",
            "/latest",
            "/summary",
            "/clear",
            "/docs"
        ],
        "scalable_cloud_design": [
            "AWS API Gateway",
            "AWS SQS",
            "AWS Lambda",
            "AWS DynamoDB"
        ]
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "cloud_backend",
        "port": BACKEND_PORT
    }


@app.post("/readings")
def receive_reading(reading: SensorReading):
    """
    Receive one processed reading from the fog node and store it.

    In the local version:
    Fog Node -> FastAPI Backend -> CSV file

    In the scalable cloud version:
    Fog Node -> API Gateway -> SQS -> Lambda -> DynamoDB
    """
    # Compatible with both Pydantic v1 and v2
    reading_dict = reading.model_dump() if hasattr(reading, "model_dump") else reading.dict()

    append_reading(reading_dict)

    print(
        f"[BACKEND] Stored reading | "
        f"Machine: {reading.machine_id} | "
        f"Status: {reading.machine_status} | "
        f"Time: {reading.timestamp}"
    )

    return {
        "status": "stored",
        "message": "Reading stored successfully.",
        "machine_id": reading.machine_id,
        "machine_status": reading.machine_status
    }


@app.get("/readings")
def get_readings(limit: int = 100):
    """
    Return recent stored readings.

    Default returns the last 100 readings.
    The dashboard uses this endpoint for charts and alert tables.
    """
    if limit <= 0:
        raise HTTPException(status_code=400, detail="Limit must be greater than 0.")

    readings = load_readings()

    return {
        "readings": readings[-limit:],
        "count": len(readings),
        "returned": min(limit, len(readings))
    }


@app.get("/latest")
def get_latest():
    """Return the most recent machine reading."""
    readings = load_readings()

    if not readings:
        return {
            "latest": None,
            "message": "No readings stored yet."
        }

    return {
        "latest": readings[-1]
    }


@app.get("/summary")
def get_summary():
    """
    Return summary statistics for the dashboard.

    Includes:
    - total readings
    - normal, warning and critical counts
    - average vibration, temperature and pressure
    """
    readings = load_readings()
    summary = calculate_summary(readings)

    return summary


@app.delete("/clear")
def clear_readings():
    """
    Clear all stored readings and reset backend CSV storage.

    This is useful before recording the final demo.
    """
    if os.path.exists(BACKEND_DATA_FILE):
        os.remove(BACKEND_DATA_FILE)

    init_storage()

    print("[BACKEND] All stored readings cleared.")

    return {
        "status": "cleared",
        "message": "All readings have been deleted and storage has been reset."
    }