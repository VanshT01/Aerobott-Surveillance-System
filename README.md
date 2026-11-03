# Aerobott Surveillance System

Real-time backend for a drone and CCTV monitoring platform, built during my software engineering internship at Aerobott (May to August 2026). It ingests live video and telemetry, runs vision models on the streams, and turns the results into stored events and security alerts.

## Features

- **Video pipeline:** RTSP ingest, WebRTC delivery, and 60-second segmented recording
- **Failure recovery:** automatic stream reconnection with exponential backoff (1 to 16 seconds)
- **Computer vision:** object detection, ReID tracking, crowd counting, and license plate recognition
- **Drone telemetry:** MQTT ingestion and geofence monitoring
- **Alerts:** Slack-compatible webhook notifications for detection and security events
- **API and storage:** 40+ REST endpoints and a 9-table PostgreSQL schema for device state, telemetry, recordings, and ML events

## Tech Stack

Python, FastAPI, SQLAlchemy, PostgreSQL, paho-mqtt, aiortc, OpenCV, PyTorch, Ultralytics YOLO, EasyOCR

## Repository Layout

```text
backend/app/
  db/            SQLAlchemy models and sessions
  repositories/  Data access
  services/
    events/         Detection event handling
    geofencing/     Geofence monitoring
    notifications/  Webhook alerts
    telemetry/      MQTT telemetry
    video/          RTSP, WebRTC, and recording
    vision/         Detection, ReID, crowd counting, license plates
backend/scripts/ CSRNet data preparation and training
frontend/        Web client
tests/           Automated tests
docs/            Project documentation
```

## Running Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp backend/.env.example backend/.env
cd backend
uvicorn app.main:app --reload
```

Set the database and camera values in `backend/.env` before starting the server.
