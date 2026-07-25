import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "industrial-fault-readings")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS"
}


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": HEADERS,
        "body": json.dumps(body)
    }


def to_dynamodb_value(value):
    """Convert floats to Decimal because DynamoDB does not accept float directly."""
    if isinstance(value, float):
        return Decimal(str(value))

    if isinstance(value, dict):
        return {k: to_dynamodb_value(v) for k, v in value.items()}

    if isinstance(value, list):
        return [to_dynamodb_value(v) for v in value]

    return value


def from_dynamodb_value(value):
    """Convert DynamoDB Decimal values back to normal JSON values."""
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)

    if isinstance(value, dict):
        return {k: from_dynamodb_value(v) for k, v in value.items()}

    if isinstance(value, list):
        return [from_dynamodb_value(v) for v in value]

    return value


def get_method_and_path(event):
    """Get HTTP method and path from API Gateway or Lambda test event."""
    http_info = event.get("requestContext", {}).get("http", {})

    method = http_info.get("method", event.get("httpMethod", "GET"))
    path = event.get("rawPath", event.get("path", "/"))

    if path.startswith("/prod/"):
        path = path.replace("/prod", "", 1)

    return method.upper(), path.rstrip("/") or "/"


def parse_body(event):
    """Parse JSON body from API Gateway event."""
    body = event.get("body")

    if not body:
        return {}

    if isinstance(body, dict):
        return body

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def scan_all_items():
    """Read all records from DynamoDB."""
    items = []
    scan_kwargs = {}

    while True:
        result = table.scan(**scan_kwargs)
        items.extend(result.get("Items", []))

        if "LastEvaluatedKey" not in result:
            break

        scan_kwargs["ExclusiveStartKey"] = result["LastEvaluatedKey"]

    items = [from_dynamodb_value(item) for item in items]
    items.sort(key=lambda x: x.get("received_at", ""))

    return items


def calculate_summary(items):
    """Calculate dashboard summary from DynamoDB records."""
    total = len(items)

    if total == 0:
        return {
            "total": 0,
            "normal_count": 0,
            "warning_count": 0,
            "critical_count": 0,
            "avg_vibration": 0,
            "avg_temperature": 0,
            "avg_pressure": 0
        }

    normal_count = sum(1 for item in items if item.get("machine_status") == "Normal")
    warning_count = sum(1 for item in items if item.get("machine_status") == "Warning")
    critical_count = sum(1 for item in items if item.get("machine_status") == "Critical")

    avg_vibration = sum(float(item.get("vibration", 0)) for item in items) / total
    avg_temperature = sum(float(item.get("temperature", 0)) for item in items) / total
    avg_pressure = sum(float(item.get("pressure", 0)) for item in items) / total

    return {
        "total": total,
        "normal_count": normal_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "avg_vibration": round(avg_vibration, 4),
        "avg_temperature": round(avg_temperature, 4),
        "avg_pressure": round(avg_pressure, 4)
    }


def lambda_handler(event, context):
    method, path = get_method_and_path(event)

    if method == "OPTIONS":
        return response(200, {"status": "ok"})

    if method == "GET" and path == "/health":
        return response(200, {
            "status": "ok",
            "service": "aws_cloud_backend",
            "table": TABLE_NAME
        })

    if method == "POST" and path == "/readings":
        payload = parse_body(event)

        if payload is None:
            return response(400, {
                "status": "error",
                "message": "Invalid JSON body"
            })

        required_fields = [
            "timestamp",
            "machine_id",
            "vibration",
            "temperature",
            "pressure",
            "machine_status",
            "alert_message"
        ]

        missing = [field for field in required_fields if field not in payload]

        if missing:
            return response(400, {
                "status": "error",
                "message": "Missing required fields",
                "missing_fields": missing
            })

        item = {
            "reading_id": str(uuid.uuid4()),
            "received_at": datetime.now(timezone.utc).isoformat(),
            **payload
        }

        table.put_item(Item=to_dynamodb_value(item))

        return response(200, {
            "status": "stored",
            "message": "Reading stored in DynamoDB",
            "reading_id": item["reading_id"],
            "machine_status": item.get("machine_status")
        })

    if method == "GET" and path == "/readings":
        query = event.get("queryStringParameters") or {}
        limit = int(query.get("limit", 100))

        items = scan_all_items()
        limited_items = items[-limit:]

        return response(200, {
            "readings": limited_items,
            "count": len(items),
            "returned": len(limited_items)
        })

    if method == "GET" and path == "/latest":
        items = scan_all_items()

        if not items:
            return response(200, {
                "latest": None,
                "message": "No readings stored yet."
            })

        return response(200, {
            "latest": items[-1]
        })

    if method == "GET" and path == "/summary":
        items = scan_all_items()
        return response(200, calculate_summary(items))

    if method == "DELETE" and path == "/clear":
        items = scan_all_items()

        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(
                    Key={
                        "reading_id": item["reading_id"]
                    }
                )

        return response(200, {
            "status": "cleared",
            "message": "All DynamoDB readings deleted."
        })

    return response(404, {
        "status": "error",
        "message": f"Route not found: {method} {path}"
    })