export function formatDate(value?: string | null): string {
  if (!value) return "N/A";
  return new Date(value).toLocaleString();
}

export function formatValue(value?: string | number | null): string {
  if (value === null || value === undefined || value === "") return "N/A";
  return String(value);
}

export function hasCoordinates(device: { latitude: string | null; longitude: string | null }): boolean {
  return !Number.isNaN(Number(device.latitude)) && !Number.isNaN(Number(device.longitude));
}
