import { useEffect, useRef, useState, type FormEvent } from "react";
import { api } from "../lib/api";
import { formatDate, formatValue } from "../lib/format";
import type { Device, DevicePayload, DeviceStatus, DeviceType } from "../types";

interface Props {
  devices: Device[];
  onChanged: () => Promise<void>;
}

interface DeviceFormState {
  id: number | null;
  name: string;
  device_type: DeviceType;
  status: DeviceStatus;
  ip_address: string;
  rtsp_url: string;
  onvif_url: string;
  latitude: string;
  longitude: string;
  location_name: string;
}

const blankForm: DeviceFormState = {
  id: null,
  name: "",
  device_type: "camera",
  status: "unknown",
  ip_address: "",
  rtsp_url: "",
  onvif_url: "",
  latitude: "",
  longitude: "",
  location_name: ""
};

function nullable(value: string): string | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

function toPayload(form: DeviceFormState, includeStatus: boolean): DevicePayload {
  return {
    name: form.name.trim(),
    device_type: form.device_type,
    ip_address: nullable(form.ip_address),
    rtsp_url: nullable(form.rtsp_url),
    onvif_url: nullable(form.onvif_url),
    latitude: nullable(form.latitude),
    longitude: nullable(form.longitude),
    location_name: nullable(form.location_name),
    ...(includeStatus ? { status: form.status } : {})
  };
}

export function DeviceManagement({ devices, onChanged }: Props) {
  const [form, setForm] = useState<DeviceFormState>(blankForm);
  const [error, setError] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);

  useEffect(() => {
    if (form.id && !devices.some((device) => device.id === form.id)) {
      setForm(blankForm);
    }
  }, [devices, form.id]);

  function update<K extends keyof DeviceFormState>(key: K, value: DeviceFormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function edit(device: Device) {
    setForm({
      id: device.id,
      name: device.name,
      device_type: device.device_type,
      status: device.status,
      ip_address: device.ip_address ?? "",
      rtsp_url: device.rtsp_url ?? "",
      onvif_url: device.onvif_url ?? "",
      latitude: device.latitude ?? "",
      longitude: device.longitude ?? "",
      location_name: device.location_name ?? ""
    });
    setError(null);
    window.requestAnimationFrame(() => {
      formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      formRef.current?.querySelector<HTMLInputElement>("input")?.focus();
    });
  }

  async function save(event: FormEvent) {
    event.preventDefault();

    if (!form.name.trim()) {
      setError("Device name is required.");
      return;
    }

    try {
      if (form.id) {
        await api.updateDevice(form.id, toPayload(form, true));
      } else {
        const created = await api.createDevice(toPayload(form, false));
        if (form.status !== "unknown") {
          await api.updateDevice(created.id, { status: form.status });
        }
      }

      setForm(blankForm);
      setError(null);
      await onChanged();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to save device.");
    }
  }

  async function remove(device: Device) {
    if (!window.confirm(`Delete ${device.name}?`)) return;

    try {
      await api.deleteDevice(device.id);
      if (form.id === device.id) {
        setForm(blankForm);
      }
      setError(null);
      await onChanged();
    } catch (removeError) {
      setError(removeError instanceof Error ? removeError.message : "Failed to delete device.");
    }
  }

  return (
    <section className="panel">
      <div className="section-header">
        <h2>Device Management</h2>
        <button type="button" onClick={() => setForm(blankForm)}>New Device</button>
      </div>

      {error && <div className="notice error">{error}</div>}

      <form ref={formRef} className="device-form" onSubmit={save}>
        <label>
          Name
          <input value={form.name} onChange={(event) => update("name", event.target.value)} required />
        </label>
        <label>
          Type
          <select value={form.device_type} onChange={(event) => update("device_type", event.target.value as DeviceType)}>
            <option value="camera">camera</option>
            <option value="drone">drone</option>
          </select>
        </label>
        <label>
          Status
          <select value={form.status} onChange={(event) => update("status", event.target.value as DeviceStatus)}>
            <option value="unknown">unknown</option>
            <option value="online">online</option>
            <option value="offline">offline</option>
          </select>
        </label>
        <label>
          IP Address
          <input value={form.ip_address} onChange={(event) => update("ip_address", event.target.value)} />
        </label>
        <label className="span-2">
          RTSP URL
          <input value={form.rtsp_url} onChange={(event) => update("rtsp_url", event.target.value)} />
        </label>
        <label>
          ONVIF URL
          <input value={form.onvif_url} onChange={(event) => update("onvif_url", event.target.value)} />
        </label>
        <label>
          Latitude
          <input value={form.latitude} onChange={(event) => update("latitude", event.target.value)} />
        </label>
        <label>
          Longitude
          <input value={form.longitude} onChange={(event) => update("longitude", event.target.value)} />
        </label>
        <label className="span-2">
          Location
          <input value={form.location_name} onChange={(event) => update("location_name", event.target.value)} />
        </label>
        <div className="form-actions">
          <button type="submit">{form.id ? "Save Changes" : "Add Device"}</button>
          <button type="button" onClick={() => setForm(blankForm)}>Clear</button>
        </div>
      </form>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Type</th>
              <th>Status</th>
              <th>RTSP</th>
              <th>Lat/Lon</th>
              <th>Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {devices.length === 0 && (
              <tr>
                <td colSpan={8} className="muted">No devices found</td>
              </tr>
            )}
            {devices.map((device) => (
              <tr key={device.id}>
                <td>{device.id}</td>
                <td>{device.name}</td>
                <td>{device.device_type}</td>
                <td>{device.status}</td>
                <td>{formatValue(device.rtsp_url)}</td>
                <td>{formatValue(device.latitude)} / {formatValue(device.longitude)}</td>
                <td>{formatDate(device.updated_at)}</td>
                <td>
                  <button type="button" onClick={() => edit(device)}>Edit</button>
                  <button type="button" className="danger" onClick={() => remove(device)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
