import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./lib/api";
import type { Device } from "./types";
import { DeviceManagement } from "./components/DeviceManagement";
import { StatusPanel } from "./components/StatusPanel";
import { StreamPanel } from "./components/StreamPanel";
import { TrackingMap } from "./components/TrackingMap";
import { EventFeed } from "./components/EventFeed";
import { GeofenceManagement } from "./components/GeofenceManagement";
import { SecurityAlerts } from "./components/SecurityAlerts";
import type { Geofence, SecurityEvent } from "./types";

const STORAGE_KEY = "surveillance_selected_device_id";
const DEVICE_REFRESH_MS = 3000;

export function App() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [geofences, setGeofences] = useState<Geofence[]>([]);
  const [securityEvents, setSecurityEvents] = useState<SecurityEvent[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [clock, setClock] = useState(new Date());

  const selectedDevice = useMemo(
    () => devices.find((device) => device.id === selectedDeviceId) ?? null,
    [devices, selectedDeviceId]
  );

  const loadDevices = useCallback(async () => {
    try {
      const data = await api.listDevices();
      setDevices(data);
      setError(null);

      const saved = Number(localStorage.getItem(STORAGE_KEY));
      const nextSelected =
        data.find((device) => device.id === selectedDeviceId)?.id ??
        data.find((device) => device.id === saved)?.id ??
        data[0]?.id ??
        null;

      setSelectedDeviceId(nextSelected);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load devices");
    }
  }, [selectedDeviceId]);

  useEffect(() => {
    loadDevices();
  }, [loadDevices]);

  const loadGeofences = useCallback(async () => {
    try {
      setGeofences(await api.listGeofences());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load geofences");
    }
  }, []);

  const loadSecurityEvents = useCallback(async () => {
    try {
      setSecurityEvents(await api.securityEvents());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load security alerts");
    }
  }, []);

  useEffect(() => {
    loadGeofences();
    loadSecurityEvents();
  }, [loadGeofences, loadSecurityEvents]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      loadDevices();
      loadSecurityEvents();
    }, DEVICE_REFRESH_MS);

    return () => window.clearInterval(timer);
  }, [loadDevices, loadSecurityEvents]);

  useEffect(() => {
    const timer = window.setInterval(() => setClock(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  function handleSelect(id: number) {
    setSelectedDeviceId(id);
    localStorage.setItem(STORAGE_KEY, String(id));
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Surveillance System</p>
          <h1>Operations Dashboard</h1>
        </div>
        <div className="clock">{clock.toLocaleString()}</div>
      </header>

      {error && <div className="alert error">{error}</div>}

      <section className="toolbar">
        <label htmlFor="deviceSelector">Selected device</label>
        <select
          id="deviceSelector"
          value={selectedDeviceId ?? ""}
          onChange={(event) => handleSelect(Number(event.target.value))}
        >
          {devices.length === 0 && <option value="">No devices found</option>}
          {devices.map((device) => (
            <option key={device.id} value={device.id}>
              {device.id} - {device.name} ({device.device_type}, {device.status})
            </option>
          ))}
        </select>
      </section>

      <StatusPanel selectedDevice={selectedDevice} />
      <TrackingMap devices={devices} geofences={geofences} />

      <StreamPanel selectedDevice={selectedDevice} onDeviceChanged={loadDevices} />

      <SecurityAlerts events={securityEvents} />
      <GeofenceManagement geofences={geofences} onChanged={loadGeofences} />
      <EventFeed selectedDevice={selectedDevice} />
      <DeviceManagement devices={devices} onChanged={loadDevices} />
    </main>
  );
}
