import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./lib/api";
import type { Device, Geofence, SecurityEvent } from "./types";
import { DeviceManagement } from "./components/DeviceManagement";
import { StatusPanel } from "./components/StatusPanel";
import { StreamPanel } from "./components/StreamPanel";
import { TrackingMap } from "./components/TrackingMap";
import { EventFeed } from "./components/EventFeed";
import { GeofenceManagement } from "./components/GeofenceManagement";
import { SecurityAlerts } from "./components/SecurityAlerts";
import { ReIDPanel } from "./components/ReIDPanel";

const STORAGE_KEY = "surveillance_selected_device_id";
const DEVICE_REFRESH_MS = 3000;

export function App() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [geofences, setGeofences] = useState<Geofence[]>([]);
  const [securityEvents, setSecurityEvents] = useState<SecurityEvent[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [securityClearError, setSecurityClearError] = useState<string | null>(null);
  const [clearingSecurityEvents, setClearingSecurityEvents] = useState(false);
  const [clock, setClock] = useState(new Date());

  const selectedDevice = useMemo(
    () => devices.find((device) => device.id === selectedDeviceId) ?? null,
    [devices, selectedDeviceId]
  );
  const onlineDevices = useMemo(
    () => devices.filter((device) => device.status === "online").length,
    [devices]
  );
  const cameraCount = useMemo(
    () => devices.filter((device) => device.device_type === "camera").length,
    [devices]
  );
  const droneCount = useMemo(
    () => devices.filter((device) => device.device_type === "drone").length,
    [devices]
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

  async function clearSecurityEvents() {
    if (securityEvents.length === 0) return;
    if (!window.confirm("Clear all security alerts from the dashboard?")) return;

    try {
      setClearingSecurityEvents(true);
      await api.deleteSecurityEvents();
      await loadSecurityEvents();
      setSecurityClearError(null);
    } catch (clearError) {
      setSecurityClearError(
        clearError instanceof Error ? clearError.message : "Failed to clear security alerts."
      );
    } finally {
      setClearingSecurityEvents(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div>
            <p className="eyebrow">Aerobott</p>
            <h1>Surveillance System</h1>
          </div>
        </div>
        <div className="topbar-meta">
          <span>Live command center</span>
          <div className="clock">{clock.toLocaleString()}</div>
        </div>
      </header>

      {error && <div className="alert error">{error}</div>}

      <section className="overview-band" aria-label="System overview">
        <div className="overview-card">
          <span>Total assets</span>
          <strong>{devices.length}</strong>
        </div>
        <div className="overview-card">
          <span>Online</span>
          <strong className={onlineDevices > 0 ? "positive" : ""}>{onlineDevices}</strong>
        </div>
        <div className="overview-card">
          <span>Cameras</span>
          <strong>{cameraCount}</strong>
        </div>
        <div className="overview-card">
          <span>Drones</span>
          <strong>{droneCount}</strong>
        </div>
        <div className="overview-card">
          <span>Alerts</span>
          <strong className={securityEvents.length > 0 ? "negative" : ""}>{securityEvents.length}</strong>
        </div>
      </section>

      <section className="command-strip">
        <div className="toolbar">
          <label htmlFor="deviceSelector">Selected asset</label>
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
        </div>
        <div className="asset-summary">
          <span className={`status-dot ${selectedDevice?.status ?? "unknown"}`} />
          <div>
            <strong>{selectedDevice?.name ?? "No asset selected"}</strong>
            <span>
              {selectedDevice
                ? `${selectedDevice.device_type} ${selectedDevice.location_name ? `- ${selectedDevice.location_name}` : ""}`
                : "Select a deployed device to inspect telemetry"}
            </span>
          </div>
        </div>
      </section>

      <StatusPanel selectedDevice={selectedDevice} />

      <section className="workspace-grid">
        <div className="primary-stack">
          <StreamPanel selectedDevice={selectedDevice} onDeviceChanged={loadDevices} />
          <TrackingMap devices={devices} geofences={geofences} />
        </div>
        <aside className="side-stack">
          <SecurityAlerts
            clearing={clearingSecurityEvents}
            error={securityClearError}
            events={securityEvents}
            onClear={clearSecurityEvents}
          />
          <ReIDPanel />
          <EventFeed selectedDevice={selectedDevice} />
        </aside>
      </section>

      <section className="management-grid">
        <DeviceManagement devices={devices} onChanged={loadDevices} />
        <GeofenceManagement geofences={geofences} onChanged={loadGeofences} />
      </section>
    </main>
  );
}
