import { useState, type FormEvent } from "react";
import { api } from "../lib/api";
import { formatDate } from "../lib/format";
import type { Geofence, GeofencePayload } from "../types";

interface Props {
  geofences: Geofence[];
  onChanged: () => Promise<void>;
}

interface GeofenceFormState {
  id: number | null;
  name: string;
  latitude: string;
  longitude: string;
  radius_meters: string;
}

const blankForm: GeofenceFormState = {
  id: null,
  name: "",
  latitude: "",
  longitude: "",
  radius_meters: "100"
};

function toPayload(form: GeofenceFormState): GeofencePayload {
  return {
    name: form.name.trim(),
    latitude: Number(form.latitude),
    longitude: Number(form.longitude),
    radius_meters: Number(form.radius_meters)
  };
}

export function GeofenceManagement({ geofences, onChanged }: Props) {
  const [form, setForm] = useState<GeofenceFormState>(blankForm);
  const [error, setError] = useState<string | null>(null);

  function update<K extends keyof GeofenceFormState>(key: K, value: GeofenceFormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function edit(geofence: Geofence) {
    setForm({
      id: geofence.id,
      name: geofence.name,
      latitude: String(geofence.latitude),
      longitude: String(geofence.longitude),
      radius_meters: String(geofence.radius_meters)
    });
    setError(null);
  }

  async function save(event: FormEvent) {
    event.preventDefault();

    if (!form.name.trim()) {
      setError("Geofence name is required.");
      return;
    }

    const payload = toPayload(form);

    if (
      Number.isNaN(payload.latitude) ||
      Number.isNaN(payload.longitude) ||
      Number.isNaN(payload.radius_meters) ||
      payload.radius_meters <= 0
    ) {
      setError("Latitude, longitude, and radius must be valid numbers.");
      return;
    }

    try {
      if (form.id) {
        await api.updateGeofence(form.id, payload);
      } else {
        await api.createGeofence(payload);
      }

      setForm(blankForm);
      setError(null);
      await onChanged();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to save geofence.");
    }
  }

  async function remove(geofence: Geofence) {
    if (!window.confirm(`Delete geofence ${geofence.name}?`)) return;

    try {
      await api.deleteGeofence(geofence.id);
      if (form.id === geofence.id) {
        setForm(blankForm);
      }
      setError(null);
      await onChanged();
    } catch (removeError) {
      setError(removeError instanceof Error ? removeError.message : "Failed to delete geofence.");
    }
  }

  return (
    <section className="panel">
      <div className="section-header">
        <h2>Geofences</h2>
        <button type="button" onClick={() => setForm(blankForm)}>New Geofence</button>
      </div>

      {error && <div className="notice error">{error}</div>}

      <form className="geofence-form" onSubmit={save}>
        <label>
          Name
          <input value={form.name} onChange={(event) => update("name", event.target.value)} required />
        </label>
        <label>
          Latitude
          <input value={form.latitude} onChange={(event) => update("latitude", event.target.value)} required />
        </label>
        <label>
          Longitude
          <input value={form.longitude} onChange={(event) => update("longitude", event.target.value)} required />
        </label>
        <label>
          Radius meters
          <input value={form.radius_meters} onChange={(event) => update("radius_meters", event.target.value)} required />
        </label>
        <div className="form-actions">
          <button type="submit">{form.id ? "Save Changes" : "Add Geofence"}</button>
          <button type="button" onClick={() => setForm(blankForm)}>Clear</button>
        </div>
      </form>

      <div className="table-wrap compact-table">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Center</th>
              <th>Radius</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {geofences.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">No geofences configured</td>
              </tr>
            )}
            {geofences.map((geofence) => (
              <tr key={geofence.id}>
                <td>{geofence.name}</td>
                <td>{geofence.latitude}, {geofence.longitude}</td>
                <td>{geofence.radius_meters}m</td>
                <td>{formatDate(geofence.created_at)}</td>
                <td>
                  <button type="button" onClick={() => edit(geofence)}>Edit</button>
                  <button type="button" className="danger" onClick={() => remove(geofence)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
