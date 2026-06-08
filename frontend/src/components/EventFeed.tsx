import { useEffect, useState } from "react";
import { api, eventSnapshotUrl } from "../lib/api";
import { isVideoDevice } from "../lib/devices";
import { formatDate } from "../lib/format";
import type { Device, EventItem } from "../types";

interface Props {
  selectedDevice: Device | null;
}

export function EventFeed({ selectedDevice }: Props) {
  const [events, setEvents] = useState<EventItem[]>([]);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!isVideoDevice(selectedDevice)) {
        setEvents([]);
        return;
      }

      try {
        const data = await api.events(selectedDevice.id);
        if (!cancelled) {
          setEvents(data);
          setError(null);
        }
      } catch {
        if (!cancelled) {
          setEvents([]);
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

  async function clearEvents() {
    if (!isVideoDevice(selectedDevice) || events.length === 0) return;
    if (!window.confirm(`Clear event feed for ${selectedDevice.name}?`)) return;

    try {
      setClearing(true);
      await api.deleteEvents(selectedDevice.id);
      setEvents([]);
      setError(null);
    } catch (clearError) {
      setError(clearError instanceof Error ? clearError.message : "Failed to clear event feed.");
    } finally {
      setClearing(false);
    }
  }

  return (
    <section className="panel">
      <div className="section-header">
        <h2>Event Feed</h2>
        <div className="actions">
          <span className="meta">{events.length} recent</span>
          <button type="button" disabled={clearing || events.length === 0} onClick={clearEvents}>
            {clearing ? "Clearing..." : "Clear"}
          </button>
        </div>
      </div>

      {error && <div className="notice error">{error}</div>}

      <div className="event-list">
        {events.length === 0 && <div className="empty">No events yet</div>}
        {events.map((event) => (
          <article key={event.id} className="event-item">
            <div>
              <strong>{event.type}</strong>
              <span>{formatDate(event.time)}</span>
            </div>
            <img src={eventSnapshotUrl(event.id)} alt={event.type} />
          </article>
        ))}
      </div>
    </section>
  );
}
