import threading
from datetime import datetime, timezone
from pathlib import Path

import cv2

import crud
from database import SessionLocal


EVENTS_DIR = Path(__file__).resolve().parent / "events"
EVENT_COOLDOWN_SECONDS = 30

last_events = {}
events_lock = threading.Lock()


def build_event_type(detection):
    class_name = detection["class"].replace("_", " ").title()
    tracking_id = detection.get("tracking_id")

    if tracking_id is None:
        return f"{class_name} detected"

    return f"{class_name} #{tracking_id} detected"


def create_detection_events(camera_id: int, detections: list[dict], frame):
    now = datetime.now(timezone.utc)

    for detection in detections:
        event_type = build_event_type(detection)
        key = (
            camera_id,
            event_type,
            detection.get("tracking_id")
        )

        with events_lock:
            last_time = last_events.get(key)

            if last_time and (now - last_time).total_seconds() < EVENT_COOLDOWN_SECONDS:
                continue

            last_events[key] = now

        camera_folder = EVENTS_DIR / f"camera{camera_id}"
        camera_folder.mkdir(parents=True, exist_ok=True)

        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
        snapshot_path = camera_folder / f"{timestamp}.jpg"

        if not cv2.imwrite(str(snapshot_path), frame):
            continue

        db = SessionLocal()

        try:
            crud.create_event(
                db=db,
                camera_id=camera_id,
                event_type=event_type,
                event_time=now,
                snapshot=str(snapshot_path)
            )
        finally:
            db.close()
