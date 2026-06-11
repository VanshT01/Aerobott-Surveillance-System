import os
import re
import tempfile
import threading
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib"))

import cv2
import torch
from ultralytics import YOLO

MODEL_PATH = Path(__file__).resolve().parents[3] / "models" / "license_plate_detector.pt"
EASYOCR_MODEL_DIR = Path(__file__).resolve().parents[3] / "models" / "easyocr"
MODEL_NAME = "license_plate_detector_yolov8"
OCR_ALLOWLIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle"}

model = None
reader = None
model_lock = threading.Lock()
reader_lock = threading.Lock()
ocr_error = None


def get_runtime_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_model_status() -> dict[str, Any]:
    return {
        "model_name": MODEL_NAME,
        "model_path": str(MODEL_PATH),
        "model_exists": MODEL_PATH.exists(),
        "runtime_device": get_runtime_device(),
        "ocr_available": _easyocr_available(),
    }


def _easyocr_available() -> bool:
    try:
        import easyocr  # noqa: F401
    except ImportError:
        return False
    return True


def _get_model() -> YOLO:
    global model

    if not MODEL_PATH.exists():
        raise RuntimeError(f"License plate model not found at {MODEL_PATH}")

    with model_lock:
        if model is None:
            model = YOLO(str(MODEL_PATH))

    return model


def _get_reader():
    global reader

    with reader_lock:
        if reader is None:
            try:
                import easyocr
            except ImportError as error:
                raise RuntimeError("easyocr is required for license plate text recognition") from error

            EASYOCR_MODEL_DIR.mkdir(parents=True, exist_ok=True)
            reader = easyocr.Reader(
                ["en"],
                gpu=get_runtime_device() == "cuda",
                model_storage_directory=str(EASYOCR_MODEL_DIR),
            )

    return reader


def _read_plate_text(frame, box: list[int]) -> str | None:
    x1, y1, x2, y2 = box
    pad = 5
    crop = frame[
        max(0, y1 + pad):min(frame.shape[0], y2 - pad),
        max(0, x1 + pad):min(frame.shape[1], x2 - pad),
    ]

    if crop.size == 0:
        return None

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    texts = _get_reader().readtext(gray, allowlist=OCR_ALLOWLIST)
    texts = sorted(texts, key=lambda item: min(point[0] for point in item[0]))
    valid_parts = []

    for _, detected_text, confidence in texts:
        detected_text = re.sub(r"[^A-Z0-9]", "", detected_text.upper())
        if len(detected_text) >= 3 and confidence >= 0.30:
            valid_parts.append(detected_text)

    if not valid_parts:
        return None

    return "".join(valid_parts)


def _safe_read_plate_text(frame, box: list[int]) -> str | None:
    global ocr_error

    try:
        return _read_plate_text(frame, box)
    except Exception as error:
        ocr_error = str(error)
        return None


def draw_license_plate_detections(frame, detections: list[dict[str, Any]]):
    annotated = frame.copy()

    for detection in detections:
        x1, y1, x2, y2 = detection["box"]
        confidence = detection["confidence"]
        text = detection.get("text")
        label = f"Plate {confidence:.2f}"

        if text:
            label = f"{text} {confidence:.2f}"

        cv2.rectangle(annotated, (x1, y1), (x2, y2), (255, 180, 0), 2)
        cv2.putText(
            annotated,
            label,
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 180, 0),
            2,
            cv2.LINE_AA,
        )

    return annotated


def detect_license_plates(
    frame,
    confidence: float = 0.10,
    read_text: bool = False,
    image_size: int = 960,
) -> dict[str, Any]:
    detector = _get_model()
    results = detector.predict(
        frame,
        conf=confidence,
        imgsz=image_size,
        device=get_runtime_device(),
        verbose=False,
    )[0]
    detections = []

    for box in results.boxes:
        class_id = int(box.cls[0])
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        detection = {
            "class": results.names[class_id],
            "confidence": round(float(box.conf[0]), 4),
            "box": [x1, y1, x2, y2],
            "text": None,
        }

        if read_text:
            detection["text"] = _safe_read_plate_text(frame, detection["box"])

        detections.append(detection)

    return {
        "model_name": MODEL_NAME,
        "model_path": str(MODEL_PATH),
        "runtime_device": get_runtime_device(),
        "confidence_threshold": confidence,
        "image_size": image_size,
        "detections": detections,
    }


def vehicle_detected(detections: list[dict[str, Any]]) -> bool:
    return any(detection.get("class") in VEHICLE_CLASSES for detection in detections)


def detect_license_plates_for_vehicles(
    frame,
    object_detections: list[dict[str, Any]],
    confidence: float = 0.05,
    read_text: bool = True,
    image_size: int = 1280,
) -> list[dict[str, Any]]:
    detector = _get_model()
    plate_detections = []

    for object_detection in object_detections:
        if object_detection.get("class") not in VEHICLE_CLASSES:
            continue

        x1, y1, x2, y2 = object_detection["box"]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(frame.shape[1], x2)
        y2 = min(frame.shape[0], y2)
        vehicle_crop = frame[y1:y2, x1:x2]

        if vehicle_crop.size == 0:
            continue

        results = detector.predict(
            vehicle_crop,
            conf=confidence,
            imgsz=image_size,
            device=get_runtime_device(),
            verbose=False,
        )[0]

        for box in results.boxes:
            class_id = int(box.cls[0])
            px1, py1, px2, py2 = map(int, box.xyxy[0])
            full_box = [x1 + px1, y1 + py1, x1 + px2, y1 + py2]
            detection = {
                "class": results.names[class_id],
                "confidence": round(float(box.conf[0]), 4),
                "box": full_box,
                "text": None,
                "vehicle_class": object_detection.get("class"),
                "vehicle_tracking_id": object_detection.get("tracking_id"),
            }

            if read_text:
                detection["text"] = _safe_read_plate_text(frame, full_box)

            plate_detections.append(detection)

    return plate_detections

