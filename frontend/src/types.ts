export type DeviceType = "camera" | "gps_tracker" | "drone";
export type DeviceStatus = "online" | "offline" | "unknown";

export interface Device {
  id: number;
  name: string;
  device_type: DeviceType;
  ip_address: string | null;
  rtsp_url: string | null;
  onvif_url: string | null;
  latitude: string | null;
  longitude: string | null;
  status: DeviceStatus;
  location_name: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface DevicePayload {
  name: string;
  device_type: DeviceType;
  ip_address: string | null;
  rtsp_url: string | null;
  onvif_url: string | null;
  latitude: string | null;
  longitude: string | null;
  location_name: string | null;
  status?: DeviceStatus;
}

export interface CameraDashboard {
  device_id: number;
  name: string;
  status: DeviceStatus;
  resolution: string;
  fps: number | null;
  last_updated: string | null;
}

export interface RecordingStatus {
  camera_id: number;
  recording: boolean;
}

export interface EventItem {
  id: number;
  camera_id: number;
  type: string;
  time: string;
  snapshot: string;
}

export interface CrowdCount {
  id: number;
  camera_id: number;
  count: number;
  model_name: string;
  created_at: string;
}

export interface CrowdModelStatus {
  model_name: string;
  model_path: string;
  configured: boolean;
  loaded: boolean;
  error: string | null;
}

export interface WebRTCAnswer {
  sdp: string;
  type: RTCSdpType;
}
