import cv2
import av
from aiortc import VideoStreamTrack
from rtsp_service import get_video_source
import numpy as np


class CameraVideoTrack(VideoStreamTrack):
    def __init__(self, rtsp_url: str):
        super().__init__()
        self.source = get_video_source(rtsp_url)
        self.cap = cv2.VideoCapture(self.source)

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        success, frame = self.cap.read()

        if not success:
            frame = 255 * np.ones((480, 640, 3), dtype=np.uint8)

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        video_frame = av.VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base

        return video_frame

    def stop(self):
        if self.cap:
            self.cap.release()
        super().stop()