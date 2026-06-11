import cv2
from app.db.session import SessionLocal
from app.db.models import Device, DeviceType, DeviceStatus
from app.services.vision.detection import get_object_tracker
from app.services.events.detection_events import create_detection_events
import time

LOCAL_WEBCAM_TARGET_FPS = 30.0
LOCAL_WEBCAM_TARGET_WIDTH = 640
LOCAL_WEBCAM_TARGET_HEIGHT = 480


def get_video_source(rtsp_url: str):
    if rtsp_url is None:
        return None

    source = rtsp_url.strip()

    if source == "0":
        return 0

    return source


def is_local_webcam_source(source) -> bool:
    return isinstance(source, int)


def open_video_capture(source):
    cap = cv2.VideoCapture(source)

    if is_local_webcam_source(source):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, LOCAL_WEBCAM_TARGET_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, LOCAL_WEBCAM_TARGET_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, LOCAL_WEBCAM_TARGET_FPS)

    return cap


def normalize_stream_fps(source, fps: float):
    if is_local_webcam_source(source):
        return LOCAL_WEBCAM_TARGET_FPS

    if fps <= 0 or fps > 120:
        return None

    return fps


def check_rtsp_stream(rtsp_url: str) -> bool:
    source = get_video_source(rtsp_url)

    if source is None:
        return False

    cap = open_video_capture(source)

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

    cap = open_video_capture(source)

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
    fps = normalize_stream_fps(source, cap.get(cv2.CAP_PROP_FPS))

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

        video_devices = (
            db.query(Device)
            .filter(Device.device_type.in_([DeviceType.camera, DeviceType.drone]))
            .all()
        )

        for device in video_devices:

            print(f"Checking {device.name}")

            online = check_rtsp_stream(
                device.rtsp_url
            )

            if online:
                device.status = DeviceStatus.online
            else:
                device.status = DeviceStatus.offline

        db.commit()
        db.close()

        time.sleep(30)

def generate_mjpeg_stream(camera_id: int, rtsp_url: str):
    source = get_video_source(rtsp_url)

    if source is None:
        return

    cap = open_video_capture(source)
    tracker = get_object_tracker(rtsp_url)

    while True:
        success, frame = cap.read()

        if not success:
            break

        raw_frame = frame.copy()
        frame, detections = tracker.track_objects(frame)
        create_detection_events(camera_id, detections, frame, raw_frame=raw_frame)
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
