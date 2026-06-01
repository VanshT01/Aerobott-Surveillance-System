import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { formatDate } from "../lib/format";
import type { CrowdCount, CrowdModelStatus, Device } from "../types";

interface Props {
  selectedDevice: Device | null;
}

export function CrowdCounting({ selectedDevice }: Props) {
  const [model, setModel] = useState<CrowdModelStatus | null>(null);
  const [counts, setCounts] = useState<CrowdCount[]>([]);
  const [busy, setBusy] = useState(false);

  async function load() {
    const [modelStatus, crowdCounts] = await Promise.all([
      api.crowdModelStatus(),
      api.crowdCounts(selectedDevice?.device_type === "camera" ? selectedDevice.id : undefined)
    ]);
    setModel(modelStatus);
    setCounts(crowdCounts);
  }

  useEffect(() => {
    load().catch(console.error);
    const timer = window.setInterval(() => load().catch(console.error), 30000);
    return () => window.clearInterval(timer);
  }, [selectedDevice?.id]);

  async function runCount() {
    if (!selectedDevice || selectedDevice.device_type !== "camera") return;

    setBusy(true);
    try {
      await api.runCrowdCount(selectedDevice.id);
      await load();
    } finally {
      setBusy(false);
    }
  }

  const latest = counts[0];

  return (
    <section className="panel">
      <div className="section-header">
        <h2>Crowd Counting</h2>
        <button onClick={runCount} disabled={busy || selectedDevice?.device_type !== "camera"}>
          {busy ? "Running..." : "Run Count"}
        </button>
      </div>

      <div className="metrics compact">
        <div>
          <span>Model</span>
          <strong className={model?.configured ? "positive" : "negative"}>
            {model?.loaded ? "Loaded" : model?.configured ? "Configured" : "Missing"}
          </strong>
        </div>
        <div>
          <span>Latest Count</span>
          <strong>{latest ? Math.round(latest.count).toLocaleString() : "N/A"}</strong>
        </div>
        <div>
          <span>Updated</span>
          <strong>{formatDate(latest?.created_at)}</strong>
        </div>
      </div>

      <div className="table-wrap compact-table">
        <table>
          <thead>
            <tr>
              <th>Camera</th>
              <th>Count</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {counts.length === 0 && (
              <tr>
                <td colSpan={3} className="muted">No crowd counts yet</td>
              </tr>
            )}
            {counts.map((count) => (
              <tr key={count.id}>
                <td>{count.camera_id}</td>
                <td>{Math.round(count.count).toLocaleString()}</td>
                <td>{formatDate(count.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
