from ultralytics import YOLO
from pathlib import Path
import threading
import cv2

MODEL_PATH = Path(__file__).resolve().parent / "yolo11n.pt"
model = YOLO(str(MODEL_PATH))
TRACKER_CONFIG = "bytetrack.yaml"
trackers = {}
trackers_lock = threading.Lock()

TARGET_CLASSES = {
    "person",
    "car",
    "truck",
    "bus",
    "motorcycle"
}


def draw_detections(frame, results):
    detections = []

    for box in results.boxes:
        class_id = int(box.cls[0])
        class_name = results.names[class_id]
        confidence = float(box.conf[0])

        if class_name not in TARGET_CLASSES:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        tracking_id = None

        if box.id is not None:
            tracking_id = int(box.id[0])

        detections.append({
            "class": class_name,
            "confidence": round(confidence, 2),
            "box": [x1, y1, x2, y2],
            "tracking_id": tracking_id
        })

        display_name = class_name.replace("_", " ").title()

        if tracking_id is not None:
            label = f"{display_name} #{tracking_id} {confidence:.2f}"
        else:
            label = f"{display_name} {confidence:.2f}"

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        cv2.putText(
            frame,
            label,
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

    return frame, detections


def detect_objects(frame):
    results = model(frame, verbose=False)[0]
    return draw_detections(frame, results)


class ObjectTracker:
    def __init__(self):
        self.model = YOLO(str(MODEL_PATH))
        self.lock = threading.Lock()

    def track_objects(self, frame):
        with self.lock:
            results = self.model.track(
                frame,
                persist=True,
                tracker=TRACKER_CONFIG,
                verbose=False
            )[0]

        return draw_detections(frame, results)


def get_object_tracker(source_key: str):
    with trackers_lock:
        if source_key not in trackers:
            trackers[source_key] = ObjectTracker()

        return trackers[source_key]
