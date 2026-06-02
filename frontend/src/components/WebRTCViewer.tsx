import type { RefObject } from "react";

interface Props {
  videoRef: RefObject<HTMLVideoElement | null>;
}

export function WebRTCViewer({ videoRef }: Props) {
  return (
    <>
      <h3>WebRTC Fallback</h3>
      <video ref={videoRef} autoPlay playsInline controls muted />
    </>
  );
}
