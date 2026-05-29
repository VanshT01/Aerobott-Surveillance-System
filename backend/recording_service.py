import os
import cv2
import time
import threading
from datetime import datetime, timezone

from database import SessionLocal
from rtsp_service import get_video_source
import crud


RECORDINGS_DIR = "recordings"
CHUNK_SECONDS = 60

active_recorders = {}


class CameraRecorder:
    def __init__(self, camera_id: int, rtsp_url: str):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.source = get_video_source(rtsp_url)
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self.record_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def record_loop(self):
        while self.running:
            self.record_one_chunk()

    def draw_overlay(self, frame, fps):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            f"Time: {current_time}",
            f"FPS: {fps:.1f}",
            f"Camera ID: {self.camera_id}",
            "Mode: Recorded Video"
        ]

        x = 15
        y = 35

        for line in lines:
            cv2.putText(
                frame,
                line,
                (x, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
                cv2.LINE_AA
            )
            y += 35

        return frame

    def record_one_chunk(self):
        cap = cv2.VideoCapture(self.source)

        if not cap.isOpened():
            print(f"Camera {self.camera_id}: could not open stream")
            cap.release()
            time.sleep(5)
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if fps <= 0 or fps > 120:
            fps = 20.0

        if width == 0 or height == 0:
            width = 640
            height = 480

        camera_folder = os.path.join(
            RECORDINGS_DIR,
            f"camera{self.camera_id}"
        )

        os.makedirs(camera_folder, exist_ok=True)

        start_time = datetime.now(timezone.utc)

        filename = start_time.strftime("%H_%M_%S.mp4")
        path = os.path.join(camera_folder, filename)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        writer = cv2.VideoWriter(
            path,
            fourcc,
            fps,
            (width, height)
        )

        if not writer.isOpened():
            print(f"Camera {self.camera_id}: could not create video writer")
            cap.release()
            return

        print(f"Recording camera {self.camera_id} to {path}")

        end_timestamp = time.time() + CHUNK_SECONDS

        while self.running and time.time() < end_timestamp:
            success, frame = cap.read()

            if not success:
                print(f"Camera {self.camera_id}: failed to read frame")
                break

            frame = cv2.resize(frame, (width, height))
            frame = self.draw_overlay(frame, fps)

            writer.write(frame)

        end_time = datetime.now(timezone.utc)

        writer.release()
        cap.release()

        if os.path.exists(path) and os.path.getsize(path) > 0:
            db = SessionLocal()

            try:
                crud.create_recording(
                    db=db,
                    camera_id=self.camera_id,
                    start_time=start_time,
                    end_time=end_time,
                    path=path
                )
            finally:
                db.close()

            print(f"Saved recording metadata for {path}")
        else:
            print(f"Recording failed or empty file: {path}")


def start_recording(camera_id: int, rtsp_url: str):
    if camera_id in active_recorders:
        return False

    recorder = CameraRecorder(camera_id, rtsp_url)
    active_recorders[camera_id] = recorder
    recorder.start()

    return True


def stop_recording(camera_id: int):
    recorder = active_recorders.get(camera_id)

    if not recorder:
        return False

    recorder.stop()
    del active_recorders[camera_id]

    return True


def is_recording(camera_id: int):
    return camera_id in active_recorders