import type {
  CameraDashboard,
  Device,
  DevicePayload,
  EventItem,
  Geofence,
  GeofencePayload,
  RecordingStatus,
  SecurityEvent,
  WebRTCAnswer
} from "../types";

export const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = data?.detail ?? response.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return data as T;
}

export const api = {
  listDevices: () => request<Device[]>("/devices"),
  createDevice: (payload: DevicePayload) =>
    request<Device>("/devices", { method: "POST", body: JSON.stringify(payload) }),
  updateDevice: (id: number, payload: Partial<DevicePayload>) =>
    request<Device>(`/devices/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteDevice: (id: number) => request<{ message: string }>(`/devices/${id}`, { method: "DELETE" }),
  checkStream: (id: number) => request<Device>(`/devices/${id}/check-stream`, { method: "POST" }),
  dashboard: (id: number) => request<CameraDashboard>(`/devices/${id}/dashboard`),
  recordingStatus: (id: number) => request<RecordingStatus>(`/devices/${id}/recording/status`),
  startRecording: (id: number) => request<{ message: string }>(`/devices/${id}/recording/start`, { method: "POST" }),
  stopRecording: (id: number) => request<{ message: string }>(`/devices/${id}/recording/stop`, { method: "POST" }),
  events: (cameraId: number, limit = 20) => request<EventItem[]>(`/events?camera_id=${cameraId}&limit=${limit}`),
  deleteEvents: (cameraId?: number) =>
    request<{ message: string; deleted_count: number }>(
      `/events${cameraId === undefined ? "" : `?camera_id=${cameraId}`}`,
      { method: "DELETE" }
    ),
  listGeofences: () => request<Geofence[]>("/geofences"),
  createGeofence: (payload: GeofencePayload) =>
    request<Geofence>("/geofences", { method: "POST", body: JSON.stringify(payload) }),
  updateGeofence: (id: number, payload: Partial<GeofencePayload>) =>
    request<Geofence>(`/geofences/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteGeofence: (id: number) => request<{ message: string }>(`/geofences/${id}`, { method: "DELETE" }),
  securityEvents: (limit = 20) => request<SecurityEvent[]>(`/security-events?limit=${limit}`),
  deleteSecurityEvents: (deviceId?: number) =>
    request<{ message: string; deleted_count: number }>(
      `/security-events${deviceId === undefined ? "" : `?device_id=${deviceId}`}`,
      { method: "DELETE" }
    ),
  webrtcOffer: (id: number, offer: RTCSessionDescriptionInit) =>
    request<WebRTCAnswer>(`/devices/${id}/webrtc`, { method: "POST", body: JSON.stringify(offer) })
};

export function liveUrl(deviceId: number): string {
  return `${API_BASE}/devices/${deviceId}/live?t=${Date.now()}`;
}

export function eventSnapshotUrl(eventId: number): string {
  return `${API_BASE}/events/${eventId}/snapshot`;
}
