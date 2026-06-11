import { useCallback, useEffect, useMemo, useState } from "react";
import { api, reidSnapshotUrl } from "../lib/api";
import { formatDate } from "../lib/format";
import type { PersonAppearance, PersonIdentity, ReIDStatus } from "../types";

export function ReIDPanel() {
  const [status, setStatus] = useState<ReIDStatus | null>(null);
  const [persons, setPersons] = useState<PersonIdentity[]>([]);
  const [appearances, setAppearances] = useState<PersonAppearance[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);

  const selectedPerson = useMemo(
    () => persons.find((person) => person.id === selectedId) ?? null,
    [persons, selectedId]
  );

  const loadPersons = useCallback(async () => {
    try {
      const [statusData, personData] = await Promise.all([
        api.reidStatus(),
        api.reidPersons()
      ]);

      setStatus(statusData);
      setPersons(personData);
      setSelectedId((current) =>
        current !== null && personData.some((person) => person.id === current)
          ? current
          : personData[0]?.id ?? null
      );
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load ReID data.");
    }
  }, []);

  useEffect(() => {
    loadPersons();
    const timer = window.setInterval(loadPersons, 5000);
    return () => window.clearInterval(timer);
  }, [loadPersons]);

  useEffect(() => {
    let cancelled = false;

    async function loadAppearances() {
      if (selectedId === null) {
        setAppearances([]);
        return;
      }

      try {
        const data = await api.reidAppearances(selectedId, true);
        if (!cancelled) setAppearances(data);
      } catch (loadError) {
        if (!cancelled) {
          setAppearances([]);
          setError(loadError instanceof Error ? loadError.message : "Failed to load appearances.");
        }
      }
    }

    loadAppearances();
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  async function resetReID() {
    if (resetting) return;
    if (!window.confirm("Clear all ReID identities and appearance snapshots?")) return;

    try {
      setResetting(true);
      await api.deleteReidData();
      setPersons([]);
      setAppearances([]);
      setSelectedId(null);
      await loadPersons();
      setError(null);
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "Failed to reset ReID data.");
    } finally {
      setResetting(false);
    }
  }

  return (
    <section className="panel reid-panel">
      <div className="section-header">
        <h2>ReID</h2>
        <div className="actions">
          <span className="meta">
            {status ? `${status.embedding_backend} / ${status.match_threshold.toFixed(2)}` : "loading"}
          </span>
          <button type="button" disabled={resetting || persons.length === 0} onClick={resetReID}>
            {resetting ? "Resetting..." : "Reset"}
          </button>
        </div>
      </div>

      {error && <div className="notice error">{error}</div>}
      {status && !status.torchreid_loaded && (
        <div className="notice">
          Embeddings are running with fallback visual matching.
        </div>
      )}

      <div className="reid-layout">
        <div className="reid-person-list">
          {persons.length === 0 && <div className="empty">No people captured yet</div>}
          {persons.map((person) => (
            <button
              key={person.id}
              type="button"
              className={person.id === selectedId ? "selected" : ""}
              onClick={() => setSelectedId(person.id)}
            >
              <strong>{person.label}</strong>
              <span>{person.appearance_count} appearances</span>
              <span>{person.last_seen ? formatDate(person.last_seen) : "Not seen yet"}</span>
            </button>
          ))}
        </div>

        <div className="reid-appearance-list">
          <div className="reid-subhead">
            <strong>{selectedPerson?.label ?? "Select a person"}</strong>
            <span>{appearances.length} today</span>
          </div>

          {selectedId !== null && appearances.length === 0 && (
            <div className="empty">No appearances today</div>
          )}

          {appearances.map((appearance) => (
            <article key={appearance.id} className="reid-appearance">
              <img src={reidSnapshotUrl(appearance.id)} alt={`Appearance ${appearance.id}`} />
              <div>
                <strong>Camera {appearance.camera_id}</strong>
                <span>{formatDate(appearance.time)}</span>
                <span>
                  {appearance.similarity === null
                    ? "New identity"
                    : `Match ${(appearance.similarity * 100).toFixed(1)}%`}
                </span>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
