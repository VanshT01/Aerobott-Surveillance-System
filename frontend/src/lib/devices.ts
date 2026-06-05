import type { Device } from "../types";

export function isVideoDevice(device: Device | null | undefined): device is Device {
  return device?.device_type === "camera" || device?.device_type === "drone";
}
