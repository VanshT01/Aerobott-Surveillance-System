interface Props {
  message: string;
  messageType: "info" | "error";
  streamUrl: string | null;
}

export function MjpegViewer({ message, messageType, streamUrl }: Props) {
  return (
    <>
      {message && <div className={`notice ${messageType}`}>{message}</div>}
      {streamUrl && <img className="video-frame" src={streamUrl} alt="MJPEG stream" />}
    </>
  );
}
