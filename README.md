# Fog-Based Industrial Machine Fault Detection and Predictive Maintenance System

## Project Overview

This project implements a Fog and Edge Computing based industrial machine monitoring system. The system simulates machine sensor readings, processes the readings at a virtual fog node and forwards the processed data to a scalable cloud backend. A Streamlit dashboard named **ForgeWatch** displays live machine health, sensor trends, fog-computed metrics and fault alerts.

The project demonstrates how fog computing can perform quick local decision-making close to the sensor source, while cloud services provide scalable storage and dashboard access.

---

## Project Title

**Fog-Based Industrial Machine Fault Detection and Predictive Maintenance System**

---

## Dashboard Name

**ForgeWatch: Fog-to-Cloud Condition Monitoring Dashboard**

---

## System Architecture

```text
Industrial Fault Detection Dataset
            ↓
Sensor Simulator
sensor_layer/sensor_simulator.py
            ↓
Fog Node
fog_layer/fog_node.py
            ↓
AWS API Gateway
            ↓
AWS Lambda
            ↓
AWS DynamoDB
            ↓
Streamlit Dashboard
dashboard/app.py
```

---

## Architecture Explanation

The project contains four main layers:

### 1. Sensor Layer

The sensor layer is implemented using a Python sensor simulator. It reads industrial machine data from a CSV dataset and sends each row as a simulated sensor reading to the fog node.

Sensor types used:

- Vibration sensor
- Temperature sensor
- Pressure sensor

### 2. Fog Layer

The fog node is implemented using Flask. It receives raw sensor readings from the sensor simulator, performs local processing and classifies machine condition before forwarding the enriched data to the cloud backend.

The fog node calculates:

- Rolling RMS vibration
- Rolling mean temperature
- Vibration anomaly flag
- Temperature anomaly flag
- Pressure anomaly flag
- Machine status
- Alert message

### 3. Cloud Backend Layer

The cloud backend is implemented using AWS services:

- AWS API Gateway for public HTTP endpoint
- AWS Lambda for serverless backend processing
- AWS DynamoDB for scalable cloud storage

For local testing, a FastAPI backend is also included.

### 4. Dashboard Layer

The dashboard is implemented using Streamlit and Plotly. It connects to the backend and visualises the processed machine readings.

The dashboard shows:

- Latest machine status
- Vibration, temperature and pressure values
- Normal, warning and critical counts
- Sensor trend charts
- Fog-computed rolling metrics
- Warning and critical alerts
- Data explorer table

---

## Dataset

Dataset file used: https://www.kaggle.com/datasets/ziya07/industrial-iot-fault-detection-dataset

```text
data/industrial_fault_detection_data_1000.csv
```

The dataset contains industrial machine sensor readings.

Main columns used:

| Column | Description |
|---|---|
| Timestamp | Time of sensor reading |
| Vibration (mm/s) | Vibration sensor reading |
| Temperature (°C) | Machine temperature reading |
| Pressure (bar) | Machine pressure reading |
| Fault Label | Original fault label from dataset |

The project uses three main sensor types:

```text
Vibration
Temperature
Pressure
```

The dataset also contains `RMS Vibration` and `Mean Temp`, but these are not directly used as main input features. Instead, the fog node calculates rolling RMS vibration and rolling mean temperature itself. This makes the fog processing more meaningful.

---

## Fault Label Mapping

For project demonstration, the dataset fault labels are interpreted as:

| Fault Label | Meaning |
|---|---|
| 0 | Normal |
| 1 | Warning |
| 2 | Critical |

---

## Fog Processing Rules

The fog node uses simple threshold-based logic.

| Sensor | Threshold | Meaning |
|---|---|---|
| Vibration | >= 0.75 mm/s | Possible vibration or bearing fault |
| Temperature | >= 110 °C | Possible overheating |
| Pressure | >= 9.5 bar | Possible pressure abnormality |

Machine status classification:

| Condition | Machine Status |
|---|---|
| No abnormal sensor values | Normal |
| One abnormal sensor value | Warning |
| Two or more abnormal sensor values | Critical |

---

## Project Folder Structure

```text
industrial-fog-fault-detection/
├── cloud_backend/
│   └── backend.py
├── aws_lambda/
│   └── lambda_function.py
├── dashboard/
│   └── app.py
├── fog_layer/
│   └── fog_node.py
├── sensor_layer/
│   └── sensor_simulator.py
├── data/
│   └── industrial_fault_detection_data_1000.csv
├── README.md
├── requirements.txt
└── .gitignore
```

---

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| Flask | Fog node server |
| FastAPI | Local backend API |
| Uvicorn | Runs FastAPI backend |
| Requests | Sends HTTP requests between layers |
| Pandas | Data handling |
| Streamlit | Dashboard |
| Plotly | Dashboard charts |
| AWS API Gateway | Public cloud API endpoint |
| AWS Lambda | Serverless backend processing |
| AWS DynamoDB | Cloud data storage |

---

## Ports Used

The project avoids the default ports 8000, 5000 and 8501.

| Component | Port |
|---|---|
| Local FastAPI Backend | 9000 |
| Fog Node | 7000 |
| Streamlit Dashboard | 8502 |

---

## Installation Steps

### 1. Open the project folder

```powershell
cd industrial-fog-fault-detection
```

### 2. Create virtual environment

```powershell
python -m venv .venv
```

### 3. Activate virtual environment

```powershell
.venv\Scripts\activate
```

### 4. Install requirements

```powershell
pip install -r requirements.txt
```

---

## Local Testing Without AWS

The local version uses:

```text
Sensor Simulator → Fog Node → FastAPI Backend → Streamlit Dashboard
```

### Terminal 1: Start local backend

```powershell
uvicorn cloud_backend.backend:app --host 0.0.0.0 --port 9000
```

Check backend:

```text
http://localhost:9000
http://localhost:9000/docs
http://localhost:9000/health
```

---

### Terminal 2: Start fog node

```powershell
python fog_layer/fog_node.py
```

Check fog node:

```text
http://localhost:7000
http://localhost:7000/health
```

---

### Terminal 3: Start sensor simulator

```powershell
python sensor_layer/sensor_simulator.py --count 100 --generate-interval 1 --dispatch-interval 2 --fog-url http://localhost:7000/ingest
```

---

### Terminal 4: Start Streamlit dashboard

```powershell
streamlit run dashboard/app.py --server.address 0.0.0.0 --server.port 8502
```

Open dashboard:

```text
http://localhost:8502
```

In the dashboard sidebar, use backend endpoint:

```text
http://localhost:9000
```

---

## AWS Cloud Deployment

The AWS cloud backend uses:

```text
Fog Node → AWS API Gateway → AWS Lambda → AWS DynamoDB
```

### AWS Services Created

| AWS Service | Name / Purpose |
|---|---|
| DynamoDB Table | industrial-fault-readings |
| Lambda Function | industrial-fault-api |
| API Gateway | industrial-fault-http-api |

---

## DynamoDB Configuration

DynamoDB table name:

```text
industrial-fault-readings
```

Primary key:

```text
reading_id
```

Primary key type:

```text
String
```

Table capacity mode:

```text
On-demand
```

---

## Lambda Configuration

Lambda function name:

```text
industrial-fault-api
```

Runtime:

```text
Python 3.12
```

Execution role:

```text
LabRole
```

Environment variable:

```text
TABLE_NAME = industrial-fault-readings
```

The Lambda function supports these API routes:

```text
GET /health
POST /readings
GET /readings
GET /latest
GET /summary
DELETE /clear
```

---

## API Gateway Configuration

API name:

```text
industrial-fault-http-api
```

API type:

```text
HTTP API
```

Route:

```text
ANY /{proxy+}
```

Integration target:

```text
industrial-fault-api Lambda function
```

Stage:

```text
$default
```

Auto-deploy:

```text
Enabled
```

---

## AWS API Testing (Invoke URL is added on the code)

After creating API Gateway, test these URLs in the browser.

Health check:

```text
https://YOUR_API_GATEWAY_INVOKE_URL/health
```

Expected result:

```json
{
  "status": "ok",
  "service": "aws_cloud_backend",
  "table": "industrial-fault-readings"
}
```

Summary check:

```text
https://YOUR_API_GATEWAY_INVOKE_URL/summary
```

Expected result:

```json
{
  "total": 1,
  "normal_count": 0,
  "warning_count": 0,
  "critical_count": 1,
  "avg_vibration": 0.82,
  "avg_temperature": 115.2,
  "avg_pressure": 9.7
}
```

---

## Connecting Fog Node to AWS

To send fog-processed readings to AWS, update this line in:

```text
fog_layer/fog_node.py
```

Local backend URL:

```python
BACKEND_URL = "http://localhost:9000/readings"
```

AWS backend URL:

```python
BACKEND_URL = "https://YOUR_API_GATEWAY_INVOKE_URL/readings"
```

Example format:

```python
BACKEND_URL = "https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/readings"
```

After changing this URL, restart the fog node.

---

## Running the AWS Version

For the AWS version, the local FastAPI backend is not required.

### Terminal 1: Start fog node

```powershell
python fog_layer/fog_node.py
```

The terminal should show the AWS backend endpoint.

### Terminal 2: Start sensor simulator

```powershell
python sensor_layer/sensor_simulator.py --count 100 --generate-interval 1 --dispatch-interval 1 --fog-url http://localhost:7000/ingest
```

The fog node should show:

```text
[FOG -> BACKEND] Forwarded successfully. Status: Normal
[FOG -> BACKEND] Forwarded successfully. Status: Warning
[FOG -> BACKEND] Forwarded successfully. Status: Critical
```

Then check DynamoDB:

```text
DynamoDB → Tables → industrial-fault-readings → Explore table items
```

There should be multiple stored records.

---

## Connecting Dashboard to AWS

Run dashboard:

```powershell
streamlit run dashboard/app.py --server.address 0.0.0.0 --server.port 8502
```

Open:

```text
http://localhost:8502
```

In the dashboard sidebar, enter only the API Gateway base URL:

```text
https://YOUR_API_GATEWAY_INVOKE_URL
```

Do not add `/readings` in the dashboard backend field.

Correct:

```text
https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com
```

Wrong:

```text
https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/readings
```

The dashboard automatically calls:

```text
/summary
/latest
/readings
```

---

## Dashboard Features

The ForgeWatch dashboard includes:

### Live Overview

- Machine status
- Latest vibration
- Latest temperature
- Latest pressure
- Healthy sample percentage

### Sensor Trends

- Vibration trend
- Temperature trend
- Pressure trend
- Machine condition mix

### Fog Analytics

- Rolling RMS vibration
- Rolling mean temperature

### Alerts

- Warning events
- Critical events
- Diagnostic alert messages

### Data Explorer

- Full readings table
- Normal, warning and critical count
- Download CSV option

---

## Example Successful Output

### Fog Node Output

```text
[FOG] Received reading from MACHINE-001
Vibration: 0.7588 mm/s | Temperature: 119.84 °C | Pressure: 9.72 bar
-> Machine Status: Critical
-> Alert: Critical alert: High vibration detected >= 0.75 mm/s; Overheating detected >= 110.0 °C; High pressure detected >= 9.5 bar
[FOG -> BACKEND] Forwarded successfully. Status: Critical
```

### Sensor Simulator Output

```text
[SENSOR] Sending reading 53/100 to fog node...
Fog response: accepted | Machine status: Critical
```

### API Health Output

```json
{
  "status": "ok",
  "service": "aws_cloud_backend",
  "table": "industrial-fault-readings"
}
```

---

## Troubleshooting

### Backend not reachable in dashboard

Check that the backend URL is correct.

For local backend:

```text
http://localhost:9000
```

For AWS backend:

```text
https://YOUR_API_GATEWAY_INVOKE_URL
```

Do not include `/readings` in the dashboard backend field.

---

### Fog node is not receiving sensor data

Make sure fog node is running:

```powershell
python fog_layer/fog_node.py
```

Then run the sensor simulator:

```powershell
python sensor_layer/sensor_simulator.py --count 100 --generate-interval 1 --dispatch-interval 1 --fog-url http://localhost:7000/ingest
```

---

### DynamoDB has no new records

Check these:

1. API Gateway invoke URL is correct.
2. `BACKEND_URL` in `fog_node.py` ends with `/readings`.
3. Lambda environment variable is correct:

```text
TABLE_NAME = industrial-fault-readings
```

4. Lambda role is:

```text
LabRole
```

5. Fog node terminal shows:

```text
[FOG -> BACKEND] Forwarded successfully.
```

---

This project demonstrates a working fog-to-cloud IoT architecture for industrial machine fault detection. The fog node performs local processing and quick classification, while AWS provides a scalable backend using serverless and managed cloud services. The Streamlit dashboard provides a clear interface for monitoring machine health, sensor trends and fault alerts.