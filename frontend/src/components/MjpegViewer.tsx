import { LiveStreamOverlay } from "./LiveStreamOverlay";

interface Props {
  cameraId: number | null;
  fps: number | null;
  message: string;
  messageType: "info" | "error";
  streamUrl: string | null;
}

export function MjpegViewer({ cameraId, fps, message, messageType, streamUrl }: Props) {
  return (
    <>
      {message && <div className={`notice ${messageType}`}>{message}</div>}
      {streamUrl && (
        <div className="stream-stage">
          <img className="video-frame" src={streamUrl} alt="MJPEG stream" />
          <LiveStreamOverlay cameraId={cameraId} fps={fps} />
        </div>
      )}
    </>
  );
}
