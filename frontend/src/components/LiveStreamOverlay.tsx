import { useEffect, useMemo, useState } from "react";

interface Props {
  cameraId: number | null;
  fps: number | null;
}

function formatOverlayTime(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

function normalizeFps(fps: number | null): number {
  if (fps === null || fps <= 0 || fps > 120) return 20.0;
  return fps;
}

export function LiveStreamOverlay({ cameraId, fps }: Props) {
  const [now, setNow] = useState(new Date());
  const displayedFps = useMemo(() => normalizeFps(fps), [fps]);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  if (cameraId === null) return null;

  return (
    <div className="stream-overlay" aria-hidden="true">
      <span>Time: {formatOverlayTime(now)}</span>
      <span>FPS: {displayedFps.toFixed(1)}</span>
      <span>Camera ID: {cameraId}</span>
      <span>Mode: Live Stream</span>
    </div>
  );
}
