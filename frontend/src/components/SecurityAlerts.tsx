import { formatDate } from "../lib/format";
import type { SecurityEvent } from "../types";

interface Props {
  events: SecurityEvent[];
}

export function SecurityAlerts({ events }: Props) {
  return (
    <section className="panel">
      <div className="section-header">
        <h2>Security Alerts</h2>
        <span className="meta">{events.length} recent</span>
      </div>

      <div className="alert-list">
        {events.length === 0 && <div className="empty">No security alerts</div>}
        {events.map((event) => (
          <article key={event.id} className="security-alert">
            <div>
              <strong>{event.message}</strong>
              <span>{formatDate(event.created_at)}</span>
            </div>
            <code>{event.latitude}, {event.longitude}</code>
          </article>
        ))}
      </div>
    </section>
  );
}
