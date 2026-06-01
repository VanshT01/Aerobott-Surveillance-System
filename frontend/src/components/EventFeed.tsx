import { useEffect, useState } from "react";
import { api, eventSnapshotUrl } from "../lib/api";
import { formatDate } from "../lib/format";
import type { Device, EventItem } from "../types";

interface Props {
  selectedDevice: Device | null;
}

export function EventFeed({ selectedDevice }: Props) {
  const [events, setEvents] = useState<EventItem[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      if (!selectedDevice || selectedDevice.device_type !== "camera") {
        setEvents([]);
        return;
      }

      try {
        const data = await api.events(selectedDevice.id);
        if (!cancelled) setEvents(data);
      } catch {
        if (!cancelled) setEvents([]);
      }
    }

    load();
    const timer = window.setInterval(load, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [selectedDevice]);

  return (
    <section className="panel">
      <div className="section-header">
        <h2>Event Feed</h2>
        <span className="meta">{events.length} recent</span>
      </div>

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
