import threading
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Queue

import cv2

from app.repositories import crud
from app.db.session import SessionLocal
from app.services.vision.license_plate_detection import (
    VEHICLE_CLASSES,
    detect_license_plates_for_vehicles,
    draw_license_plate_detections,
)


EVENTS_DIR = Path(__file__).resolve().parents[3] / "events"
LICENSE_PLATE_SCAN_COOLDOWN_SECONDS = 5
LICENSE_PLATE_EVENT_COOLDOWN_SECONDS = 30

last_events = {}
events_lock = threading.Lock()
last_plate_scans = {}
plate_scan_lock = threading.Lock()
plate_job_queue = Queue(maxsize=4)
plate_worker_started = False
plate_worker_lock = threading.Lock()


def build_event_type(detection):
    if detection["class"] == "License_Plate":
        plate_text = detection.get("text") or "UNKNOWN"
        return f"License plate '{plate_text}' detected"

    class_name = detection["class"].replace("_", " ").title()
    tracking_id = detection.get("tracking_id")

    if tracking_id is None:
        return f"{class_name} detected"

    return f"{class_name} #{tracking_id} detected"


def has_vehicle_detection(detections: list[dict]) -> bool:
    return any(detection.get("class") in VEHICLE_CLASSES for detection in detections)


def should_scan_license_plate(camera_id: int) -> bool:
    now = datetime.now(timezone.utc)

    with plate_scan_lock:
        last_scan = last_plate_scans.get(camera_id)

        if last_scan and (now - last_scan).total_seconds() < LICENSE_PLATE_SCAN_COOLDOWN_SECONDS:
            return False

        last_plate_scans[camera_id] = now

    return True


def ensure_plate_worker_started():
    global plate_worker_started

    with plate_worker_lock:
        if plate_worker_started:
            return

        worker = threading.Thread(target=plate_worker_loop, daemon=True)
        worker.start()
        plate_worker_started = True


def schedule_license_plate_scan(camera_id: int, detections: list[dict], frame, raw_frame=None):
    if not has_vehicle_detection(detections):
        return

    if not should_scan_license_plate(camera_id):
        return

    ensure_plate_worker_started()

    detection_frame = raw_frame if raw_frame is not None else frame

    try:
        plate_job_queue.put_nowait((camera_id, detections, detection_frame.copy(), frame.copy()))
    except Exception:
        return


def plate_worker_loop():
    while True:
        try:
            camera_id, detections, raw_frame, display_frame = plate_job_queue.get(timeout=1)
        except Empty:
            continue

        try:
            create_license_plate_events(camera_id, detections, raw_frame, display_frame)
        finally:
            plate_job_queue.task_done()


def create_license_plate_events(camera_id: int, detections: list[dict], raw_frame, display_frame):
    try:
        plate_detections = detect_license_plates_for_vehicles(raw_frame, detections)
    except RuntimeError as error:
        print(f"License plate detection unavailable: {error}")
        return

    for plate_detection in plate_detections:
        event_type = build_event_type(plate_detection)
        key = (
            camera_id,
            "license_plate",
            plate_detection.get("text") or tuple(plate_detection["box"]),
        )
        now = datetime.now(timezone.utc)

        with events_lock:
            last_time = last_events.get(key)

            if last_time and (now - last_time).total_seconds() < LICENSE_PLATE_EVENT_COOLDOWN_SECONDS:
                continue

            last_events[key] = now

        camera_folder = EVENTS_DIR / f"camera{camera_id}"
        camera_folder.mkdir(parents=True, exist_ok=True)

        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
        snapshot_path = camera_folder / f"{timestamp}_license_plate.jpg"
        annotated = draw_license_plate_detections(display_frame, [plate_detection])

        if not cv2.imwrite(str(snapshot_path), annotated):
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


def create_detection_events(camera_id: int, detections: list[dict], frame, raw_frame=None):
    now = datetime.now(timezone.utc)
    schedule_license_plate_scan(camera_id, detections, frame, raw_frame=raw_frame)

    for detection in detections:
        event_type = build_event_type(detection)

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
