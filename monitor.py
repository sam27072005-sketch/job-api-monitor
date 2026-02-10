import os
import time
import csv
import json
import requests
from datetime import datetime, timezone

# Arbeitnow Job Board API (No auth)
API_URL = os.getenv("API_URL", "https://www.arbeitnow.com/api/job-board-api")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
TIMEOUT_SECONDS = float(os.getenv("TIMEOUT_SECONDS", "10"))

LOG_FILE = "monitor_log.csv"


def send_webhook_alert(message: str) -> None:
    if not WEBHOOK_URL:
        return
    # Discord uses "content", Slack uses "text"
    for payload in ({"content": message}, {"text": message}):
        try:
            requests.post(WEBHOOK_URL, json=payload, timeout=TIMEOUT_SECONDS)
            return
        except Exception:
            continue


def append_log_row(row: dict) -> None:
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main():
    started = time.time()
    timestamp = datetime.now(timezone.utc).isoformat()

    status = "DOWN"
    http_code = ""
    latency_ms = ""
    error = ""
    jobs_count = ""

    try:
        r = requests.get(API_URL, timeout=TIMEOUT_SECONDS)
        latency_ms = int((time.time() - started) * 1000)
        http_code = r.status_code

        if r.status_code != 200:
            error = f"Non-200 status: {r.status_code}"
        else:
            data = r.json()
            # Arbeitnow returns jobs inside "data"
            jobs = data.get("data", [])
            jobs_count = len(jobs)
            status = "UP"

    except Exception as e:
        latency_ms = int((time.time() - started) * 1000)
        error = str(e)[:200]

    row = {
        "timestamp_utc": timestamp,
        "api_url": API_URL,
        "status": status,
        "http_code": http_code,
        "latency_ms": latency_ms,
        "jobs_count": jobs_count,
        "error": error,
    }

    append_log_row(row)
    print(json.dumps(row, indent=2))

    if status != "UP":
        msg = (
            f"🚨 Job API Monitor Alert\n"
            f"API: {API_URL}\n"
            f"Status: {status}\n"
            f"HTTP: {http_code}\n"
            f"Latency: {latency_ms}ms\n"
            f"Error: {error}"
        )
        send_webhook_alert(msg)


if __name__ == "__main__":
    main()
