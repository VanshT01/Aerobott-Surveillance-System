import type { RefObject } from "react";
import { LiveStreamOverlay } from "./LiveStreamOverlay";

interface Props {
  cameraId: number | null;
  fps: number | null;
  live: boolean;
  videoRef: RefObject<HTMLVideoElement | null>;
}

export function WebRTCViewer({ cameraId, fps, live, videoRef }: Props) {
  return (
    <>
      <h3>WebRTC Fallback</h3>
      <div className="stream-stage">
        <video ref={videoRef} autoPlay playsInline controls muted />
        {live && <LiveStreamOverlay cameraId={cameraId} fps={fps} />}
      </div>
    </>
  );
}
