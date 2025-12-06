# Simple QR tracking and redirect app for a science project

from flask import Flask, redirect, request, send_file
import csv
from datetime import datetime
import os

app = Flask(__name__)

# Directory to store log file
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
LOG_FILE = os.path.join(DATA_DIR, "qr_scans.csv")

# Map codes (conditions / groups) to their final URLs
# You will edit these destinations to match your study design.
DESTINATIONS = {
    "conditionA": "https://forms.gle/3byQyse6MDUTWCQ68",
    "conditionB": "https://example.com/your-final-page-B"
}

# Ensure CSV has a header row if it does not exist
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_utc", "code", "ip", "user_agent", "referer"])


@app.route("/qr/<code>")
def track_and_redirect(code):
    target = DESTINATIONS.get(code)
    if not target:
        return "Unknown QR code code " + code, 404

    ts = datetime.utcnow().isoformat()
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = request.headers.get("User-Agent", "")
    referer = request.headers.get("Referer", "")

    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([ts, code, ip, ua, referer])

    return redirect(target, code=302)


@app.route("/logs/qr_scans.csv")
def download_logs():
    # Simple endpoint to download the CSV file
    if not os.path.exists(LOG_FILE):
        return "No logs yet", 404
    return send_file(LOG_FILE, as_attachment=True)


@app.route("/")
def index():
    return (
        "QR Tracker is running. Use /qr/<code> for tracking and /logs/qr_scans.csv to download logs."
    )


if __name__ == "__main__":
    # For local testing only
    app.run(host="0.0.0.0", port=5000)