import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { isVideoDevice } from "../lib/devices";
import { formatValue } from "../lib/format";
import type { CameraDashboard, CrowdCountResult, Device, RecordingStatus } from "../types";

interface Props {
  selectedDevice: Device | null;
}

export function StatusPanel({ selectedDevice }: Props) {
  const [dashboard, setDashboard] = useState<CameraDashboard | null>(null);
  const [recording, setRecording] = useState<RecordingStatus | null>(null);
  const [crowdCount, setCrowdCount] = useState<CrowdCountResult | null>(null);
  const [crowdCountError, setCrowdCountError] = useState<string | null>(null);
  const [crowdCountLoading, setCrowdCountLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!isVideoDevice(selectedDevice)) {
        setDashboard(null);
        setRecording(null);
        setCrowdCount(null);
        setCrowdCountError(null);
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

  useEffect(() => {
    setCrowdCount(null);
    setCrowdCountError(null);
    setCrowdCountLoading(false);
  }, [selectedDevice?.id]);

  async function runCrowdCount() {
    if (!isVideoDevice(selectedDevice) || crowdCountLoading) return;

    try {
      setCrowdCountLoading(true);
      setCrowdCountError(null);
      setCrowdCount(await api.crowdCount(selectedDevice.id));
    } catch (error) {
      setCrowdCount(null);
      setCrowdCountError(error instanceof Error ? error.message : "Crowd count failed.");
    } finally {
      setCrowdCountLoading(false);
    }
  }

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
        <strong>{recording?.recording ? "Recording" : isVideoDevice(selectedDevice) ? "Not recording" : "N/A"}</strong>
      </div>
      <div>
        <span>Resolution</span>
        <strong>{formatValue(dashboard?.resolution)}</strong>
      </div>
      <div>
        <span>FPS</span>
        <strong>{formatValue(dashboard?.fps)}</strong>
      </div>
      <div className="metric-action">
        <span>Crowd Count</span>
        <button type="button" disabled={!isVideoDevice(selectedDevice) || crowdCountLoading} onClick={runCrowdCount}>
          {crowdCountLoading ? "Counting..." : "Estimate"}
        </button>
      </div>
      <div>
        <span>Predicted Count</span>
        <strong>{crowdCount ? Math.max(0, Math.round(crowdCount.count)).toString() : "N/A"}</strong>
      </div>
      {crowdCountError && <div className="metric-message negative">{crowdCountError}</div>}
    </section>
  );
}
