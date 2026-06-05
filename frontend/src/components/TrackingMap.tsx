import { useEffect, useMemo, useRef } from "react";
import L from "leaflet";
import type { Device, Geofence } from "../types";
import { hasCoordinates } from "../lib/format";

interface Props {
  devices: Device[];
  geofences: Geofence[];
}

export function TrackingMap({ devices, geofences }: Props) {
  const mapEl = useRef<HTMLDivElement | null>(null);
  const map = useRef<L.Map | null>(null);
  const markers = useRef<Map<number, L.CircleMarker>>(new Map());
  const circles = useRef<Map<number, L.Circle>>(new Map());

  const trackingDevices = useMemo(
    () =>
      devices.filter(
        (device) =>
          device.device_type === "drone" &&
          hasCoordinates(device)
      ),
    [devices]
  );

  useEffect(() => {
    if ((trackingDevices.length === 0 && geofences.length === 0) || !mapEl.current) return;

    if (!map.current) {
      map.current = L.map(mapEl.current).setView([19.076, 72.877], 12);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors"
      }).addTo(map.current);
    }

    const activeIds = new Set(trackingDevices.map((device) => device.id));
    const bounds: [number, number][] = [];

    trackingDevices.forEach((device) => {
      const point: [number, number] = [Number(device.latitude), Number(device.longitude)];
      bounds.push(point);

      let marker = markers.current.get(device.id);

      if (!marker) {
        marker = L.circleMarker(point, {
          radius: 9,
          color: "#fff",
          weight: 3,
          fillColor: "#d64545",
          fillOpacity: 1
        }).addTo(map.current as L.Map);
        markers.current.set(device.id, marker);
      }

      marker.setLatLng(point);
      marker.bindPopup(`${device.name}<br>${device.device_type}<br>${device.status}<br>${device.latitude}, ${device.longitude}`);
    });

    markers.current.forEach((marker, id) => {
      if (!activeIds.has(id)) {
        marker.remove();
        markers.current.delete(id);
      }
    });

    const activeGeofenceIds = new Set(geofences.map((geofence) => geofence.id));

    geofences.forEach((geofence) => {
      const center: [number, number] = [geofence.latitude, geofence.longitude];
      bounds.push(center);

      let circle = circles.current.get(geofence.id);

      if (!circle) {
        circle = L.circle(center, {
          radius: geofence.radius_meters,
          color: "#2f6fed",
          weight: 2,
          fillColor: "#2f6fed",
          fillOpacity: 0.08
        }).addTo(map.current as L.Map);
        circles.current.set(geofence.id, circle);
      }

      circle.setLatLng(center);
      circle.setRadius(geofence.radius_meters);
      circle.bindPopup(`${geofence.name}<br>${geofence.radius_meters}m radius`);
    });

    circles.current.forEach((circle, id) => {
      if (!activeGeofenceIds.has(id)) {
        circle.remove();
        circles.current.delete(id);
      }
    });

    if (bounds.length === 0) {
      map.current.setView([19.076, 72.877], 12);
    } else if (bounds.length === 1) {
      map.current.setView(bounds[0], 17);
    } else {
      map.current.fitBounds(bounds, { padding: [32, 32] });
    }

    window.setTimeout(() => map.current?.invalidateSize(), 0);
  }, [trackingDevices, geofences]);

  if (trackingDevices.length === 0 && geofences.length === 0) return null;

  return (
    <section className="panel">
      <div className="section-header">
        <h2>Tracking Map</h2>
        <span className="meta">{trackingDevices.length} drones, {geofences.length} geofences</span>
      </div>
      <div ref={mapEl} className="map" />
    </section>
  );
}
