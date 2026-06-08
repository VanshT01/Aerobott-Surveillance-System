import json
import os
import threading
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any


DEFAULT_TIMEOUT_SECONDS = 3.0


def _isoformat(value: Any):
    if isinstance(value, datetime):
        return value.isoformat()

    return value


def _event_target_url() -> str | None:
    return os.getenv("EVENT_WEBHOOK_URL") or os.getenv("WEBHOOK_URL")


def _security_alert_target_url() -> str | None:
    return os.getenv("SECURITY_ALERT_WEBHOOK_URL") or os.getenv("WEBHOOK_URL")


def _timeout_seconds() -> float:
    try:
        return float(os.getenv("WEBHOOK_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def build_event_payload(event) -> dict[str, Any]:
    return {
        "text": f"Detection event: {event.type} on camera {event.camera_id}",
        "type": "event",
        "event": {
            "id": event.id,
            "camera_id": event.camera_id,
            "type": event.type,
            "time": _isoformat(event.time),
            "snapshot": event.snapshot,
        },
    }


def build_security_alert_payload(event) -> dict[str, Any]:
    return {
        "text": f"Security alert: {event.message}",
        "type": "security_alert",
        "security_alert": {
            "id": event.id,
            "event_type": event.event_type,
            "device_id": event.device_id,
            "geofence_id": event.geofence_id,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "message": event.message,
            "created_at": _isoformat(event.created_at),
        },
    }


def _post_json(url: str, payload: dict[str, Any]):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "surveillance-system-webhook/1.0",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=_timeout_seconds()) as response:
        response.read()


def dispatch_webhook(url: str | None, payload: dict[str, Any]):
    if not url:
        return

    def worker():
        try:
            _post_json(url, payload)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError) as error:
            print(f"Webhook delivery failed: {error}")

    threading.Thread(target=worker, daemon=True).start()


def notify_event(event):
    dispatch_webhook(_event_target_url(), build_event_payload(event))


def notify_security_alert(event):
    dispatch_webhook(_security_alert_target_url(), build_security_alert_payload(event))
