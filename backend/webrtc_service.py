import cv2
import av
import numpy as np
from aiortc import VideoStreamTrack

from rtsp_service import get_video_source
from detection_service import get_object_tracker
from event_service import create_detection_events


class CameraVideoTrack(VideoStreamTrack):
    def __init__(self, camera_id: int, rtsp_url: str):
        super().__init__()
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.source = get_video_source(rtsp_url)
        self.cap = cv2.VideoCapture(self.source)
        self.tracker = get_object_tracker(rtsp_url)

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        success, frame = self.cap.read()

        if not success:
            frame = 255 * np.ones((480, 640, 3), dtype=np.uint8)
        else:
            frame, detections = self.tracker.track_objects(frame)
            create_detection_events(self.camera_id, detections, frame)

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        video_frame = av.VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base

        return video_frame

    def stop(self):
        if self.cap:
            self.cap.release()
        super().stop()
