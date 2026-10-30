# CivicAI

CivicAI is a beginner-friendly Flask + SQLite prototype for collecting community complaints and helping city teams triage them.

## Requirements
- macOS with Python 3.10 or newer
- Internet access in the browser for Leaflet and OpenStreetMap map tiles

## Run in VS Code on macOS

1. Unzip `CivicAI-Project.zip`.
2. In VS Code, choose **File → Open Folder…** and select the unzipped `CivicAI-Project` folder.
3. Choose **Terminal → New Terminal**.
4. Run these commands one at a time:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 app.py
```

If `.venv` already exists, you can skip the first command. Keep the terminal running while using the app. Stop it with **Control-C**.

## Open the app
- Complaint form: http://127.0.0.1:5001/
- Dashboard: http://127.0.0.1:5001/complaints
- After submitting, use the tracking URL shown by the app (`/track/<complaint-id>`).

## What it includes
- Complaint form with optional photo upload and map pin
- Rule-based category, summary, priority, and department recommendation
- Duplicate-report flagging using text similarity and exact typed-location matching
- Dashboard statistics, map markers, heat layer, and area counts
- Department assignment and status updates
- 36 fictional demo reports, seeded once on first startup

## Test
Run a syntax check with:

```bash
python3 -m py_compile app.py
```

Submit a sample pothole complaint, check the receipt/tracking page, open the dashboard, and try updating the department and status.

## Limitations
This is an explainable rule-based demo, not a trained AI model. The duplicate detector can make mistakes and only compares reports with exactly matching typed locations. Demo coordinates are fictional. Photos are stored but not interpreted by AI. Map tiles and Leaflet require internet access. There is no login or role-based access; use synthetic/demo data only. The Flask development server is for local demonstration, not production deployment.
