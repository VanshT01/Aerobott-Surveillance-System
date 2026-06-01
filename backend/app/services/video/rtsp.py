import cv2
from app.db.session import SessionLocal
from app.db.models import Device, DeviceType, DeviceStatus
from app.services.vision.detection import get_object_tracker
from app.services.events.detection_events import create_detection_events
import time


def get_video_source(rtsp_url: str):
    if rtsp_url is None:
        return None

    source = rtsp_url.strip()

    if source == "0":
        return 0

    return source


def check_rtsp_stream(rtsp_url: str) -> bool:
    source = get_video_source(rtsp_url)

    if source is None:
        return False

    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        cap.release()
        return False

    success, frame = cap.read()

    cap.release()

    return success


def get_stream_info(rtsp_url: str):
    source = get_video_source(rtsp_url)

    if source is None:
        return {
            "is_opened": False,
            "width": None,
            "height": None,
            "fps": None
        }

    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        cap.release()
        return {
            "is_opened": False,
            "width": None,
            "height": None,
            "fps": None
        }

    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fps = cap.get(cv2.CAP_PROP_FPS)

    cap.release()

    return {
        "is_opened": True,
        "width": width,
        "height": height,
        "fps": fps
    }

def monitor_cameras():
    while True:

        db = SessionLocal()

        cameras = (
            db.query(Device)
            .filter(Device.device_type == DeviceType.camera)
            .all()
        )

        for camera in cameras:

            print(f"Checking {camera.name}")

            online = check_rtsp_stream(
                camera.rtsp_url
            )

            if online:
                camera.status = DeviceStatus.online
            else:
                camera.status = DeviceStatus.offline

        db.commit()
        db.close()

        time.sleep(30)

def generate_mjpeg_stream(camera_id: int, rtsp_url: str):
    source = get_video_source(rtsp_url)

    if source is None:
        return

    cap = cv2.VideoCapture(source)
    tracker = get_object_tracker(rtsp_url)

    while True:
        success, frame = cap.read()

        if not success:
            break

        frame, detections = tracker.track_objects(frame)
        create_detection_events(camera_id, detections, frame)
        success, buffer = cv2.imencode(".jpg", frame)

        if not success:
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            frame_bytes +
            b"\r\n"
        )

    cap.release()
