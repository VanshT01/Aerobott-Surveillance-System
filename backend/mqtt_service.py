import json
import os

from database import SessionLocal
import crud

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None


def _get_float(payload: dict, *keys: str):
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return float(value)

    return None


def _get_device_id(topic: str, payload: dict):
    payload_device_id = payload.get("device_id")

    if payload_device_id is not None:
        return int(payload_device_id)

    parts = topic.split("/")

    for part in parts:
        if part.isdigit():
            return int(part)

    return None


def handle_tracker_payload(topic: str, payload_bytes: bytes):
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
        device_id = _get_device_id(topic, payload)
        latitude = _get_float(payload, "lat", "latitude")
        longitude = _get_float(payload, "lon", "lng", "longitude")
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"Invalid MQTT GPS payload on {topic}: {error}")
        return

    if device_id is None or latitude is None or longitude is None:
        print(f"MQTT GPS payload missing device_id/lat/lon on {topic}: {payload}")
        return

    db = SessionLocal()

    try:
        location = crud.store_gps_location(
            db=db,
            device_id=device_id,
            latitude=latitude,
            longitude=longitude
        )

        if not location:
            print(f"MQTT GPS device {device_id} was not found or is not a gps_tracker")
            return

        print(f"Stored MQTT GPS location for device {device_id}: {latitude}, {longitude}")
    finally:
        db.close()


def start_mqtt_listener():
    if mqtt is None:
        print("MQTT disabled: install paho-mqtt to receive GPS tracker telemetry")
        return None

    host = os.getenv("MQTT_HOST", "localhost")
    port = int(os.getenv("MQTT_PORT", "1883"))
    topic = os.getenv("MQTT_TOPIC", "gps/+/location")
    username = os.getenv("MQTT_USERNAME")
    password = os.getenv("MQTT_PASSWORD")

    client = mqtt.Client()

    if username:
        client.username_pw_set(username, password)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print(f"MQTT connected to {host}:{port}; subscribing to {topic}")
            client.subscribe(topic)
        else:
            print(f"MQTT connection failed with code {rc}")

    def on_message(client, userdata, message):
        handle_tracker_payload(message.topic, message.payload)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect_async(host, port, keepalive=60)
    client.loop_start()

    return client


def get_mqtt_config():
    return {
        "host": os.getenv("MQTT_HOST", "localhost"),
        "port": int(os.getenv("MQTT_PORT", "1883")),
        "topic": os.getenv("MQTT_TOPIC", "gps/+/location"),
        "installed": mqtt is not None
    }
