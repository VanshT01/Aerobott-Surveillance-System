import { formatDate } from "../lib/format";
import type { SecurityEvent } from "../types";

interface Props {
  events: SecurityEvent[];
  clearing: boolean;
  error: string | null;
  onClear: () => void;
}

export function SecurityAlerts({ clearing, error, events, onClear }: Props) {
  return (
    <section className="panel">
      <div className="section-header">
        <h2>Security Alerts</h2>
        <div className="actions">
          <span className="meta">{events.length} recent</span>
          <button type="button" disabled={clearing || events.length === 0} onClick={onClear}>
            {clearing ? "Clearing..." : "Clear"}
          </button>
        </div>
      </div>

      {error && <div className="notice error">{error}</div>}

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
