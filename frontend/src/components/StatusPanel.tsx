import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { formatValue } from "../lib/format";
import type { CameraDashboard, Device, RecordingStatus } from "../types";

interface Props {
  selectedDevice: Device | null;
}

export function StatusPanel({ selectedDevice }: Props) {
  const [dashboard, setDashboard] = useState<CameraDashboard | null>(null);
  const [recording, setRecording] = useState<RecordingStatus | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!selectedDevice || selectedDevice.device_type !== "camera") {
        setDashboard(null);
        setRecording(null);
        return;
      }

      try {
        const [dashboardData, recordingData] = await Promise.all([
          api.dashboard(selectedDevice.id),
          api.recordingStatus(selectedDevice.id)
        ]);

        if (!cancelled) {
          setDashboard(dashboardData);
          setRecording(recordingData);
        }
      } catch {
        if (!cancelled) {
          setDashboard(null);
          setRecording(null);
        }
      }
    }

    load();
    const timer = window.setInterval(load, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [selectedDevice]);

  const status = dashboard?.status ?? selectedDevice?.status ?? "unknown";

  return (
    <section className="panel metrics">
      <div>
        <span>Status</span>
        <strong className={status === "online" ? "positive" : status === "offline" ? "negative" : ""}>
          {status}
        </strong>
      </div>
      <div>
        <span>Recording</span>
        <strong>{recording?.recording ? "Recording" : selectedDevice?.device_type === "camera" ? "Not recording" : "N/A"}</strong>
      </div>
      <div>
        <span>Resolution</span>
        <strong>{formatValue(dashboard?.resolution)}</strong>
      </div>
      <div>
        <span>FPS</span>
        <strong>{formatValue(dashboard?.fps)}</strong>
      </div>
    </section>
  );
}
