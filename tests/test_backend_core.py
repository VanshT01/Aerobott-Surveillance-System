import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app import schemas
from app.db import models
from app.db.session import Base
from app.repositories import crud
from app.services.telemetry import mqtt


class BackendCoreTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def create_device(self, name, device_type):
        return crud.create_device(
            self.db,
            schemas.DeviceCreate(
                name=name,
                device_type=device_type,
                rtsp_url="0" if device_type in [models.DeviceType.camera, models.DeviceType.drone] else None,
            ),
        )

    def test_device_types_are_camera_and_drone_only(self):
        self.assertEqual(
            {device_type.value for device_type in models.DeviceType},
            {"camera", "drone"},
        )

    def test_store_gps_location_updates_drone_coordinates(self):
        drone = self.create_device("Drone 1", models.DeviceType.drone)

        location = crud.store_gps_location(
            self.db,
            device_id=drone.id,
            latitude=19.076,
            longitude=72.877,
        )

        updated = crud.get_device(self.db, drone.id)

        self.assertIsNotNone(location)
        self.assertEqual(updated.latitude, "19.076")
        self.assertEqual(updated.longitude, "72.877")
        self.assertEqual(updated.status, models.DeviceStatus.online)
        self.assertEqual(location.device_id, drone.id)

    def test_store_gps_location_rejects_camera(self):
        camera = self.create_device("Camera 1", models.DeviceType.camera)

        location = crud.store_gps_location(
            self.db,
            device_id=camera.id,
            latitude=19.076,
            longitude=72.877,
        )

        updated = crud.get_device(self.db, camera.id)

        self.assertIsNone(location)
        self.assertIsNone(updated.latitude)
        self.assertIsNone(updated.longitude)

    def test_delete_device_removes_related_rows(self):
        drone = self.create_device("Drone 1", models.DeviceType.drone)

        self.db.add(models.CameraCredentials(device_id=drone.id, username="user", password="pass"))
        self.db.add(
            models.Recording(
                camera_id=drone.id,
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                path="/tmp/test.mp4",
            )
        )
        self.db.add(
            models.Event(
                camera_id=drone.id,
                type="person",
                time=datetime.now(timezone.utc),
                snapshot="/tmp/test.jpg",
            )
        )
        self.db.add(models.GPSLocation(device_id=drone.id, latitude=19.076, longitude=72.877))
        self.db.commit()

        deleted = crud.delete_device(self.db, drone.id)

        self.assertIsNotNone(deleted)
        self.assertIsNone(crud.get_device(self.db, drone.id))
        self.assertEqual(self.db.query(models.CameraCredentials).count(), 0)
        self.assertEqual(self.db.query(models.Recording).count(), 0)
        self.assertEqual(self.db.query(models.Event).count(), 0)
        self.assertEqual(self.db.query(models.GPSLocation).count(), 0)

    def test_mqtt_payload_updates_drone_coordinates(self):
        drone = self.create_device("Drone 1", models.DeviceType.drone)
        original_session_local = mqtt.SessionLocal
        mqtt.SessionLocal = self.SessionLocal

        try:
            payload = json.dumps({"lat": 18.99, "lon": 72.82}).encode("utf-8")
            mqtt.handle_tracker_payload(f"gps/{drone.id}/location", payload)
        finally:
            mqtt.SessionLocal = original_session_local

        with self.SessionLocal() as db:
            updated = crud.get_device(db, drone.id)
            locations = crud.get_gps_locations(db, drone.id)

            self.assertEqual(updated.latitude, "18.99")
            self.assertEqual(updated.longitude, "72.82")
            self.assertEqual(updated.status, models.DeviceStatus.online)
            self.assertEqual(len(locations), 1)

    def test_geofence_exit_creates_security_event(self):
        drone = self.create_device("Drone 1", models.DeviceType.drone)
        crud.create_geofence(
            self.db,
            schemas.GeofenceCreate(
                name="Base",
                latitude=19.076,
                longitude=72.877,
                radius_meters=100,
            ),
        )

        crud.store_gps_location(
            self.db,
            device_id=drone.id,
            latitude=19.086,
            longitude=72.877,
        )

        events = crud.get_security_events(self.db)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "geofence_exit")
        self.assertEqual(events[0].device_id, drone.id)
        self.assertIn("outside geofence Base", events[0].message)

    def test_geofence_exit_creates_event_for_each_outside_geofence(self):
        drone = self.create_device("Drone 1", models.DeviceType.drone)
        crud.create_geofence(
            self.db,
            schemas.GeofenceCreate(
                name="Base A",
                latitude=19.076,
                longitude=72.877,
                radius_meters=100,
            ),
        )
        crud.create_geofence(
            self.db,
            schemas.GeofenceCreate(
                name="Base B",
                latitude=19.08,
                longitude=72.88,
                radius_meters=100,
            ),
        )

        crud.store_gps_location(
            self.db,
            device_id=drone.id,
            latitude=19.086,
            longitude=72.877,
        )

        events = crud.get_security_events(self.db)
        messages = {event.message for event in events}

        self.assertEqual(len(events), 2)
        self.assertTrue(any("Base A" in message for message in messages))
        self.assertTrue(any("Base B" in message for message in messages))

    def test_geofence_inside_does_not_create_security_event(self):
        drone = self.create_device("Drone 1", models.DeviceType.drone)
        crud.create_geofence(
            self.db,
            schemas.GeofenceCreate(
                name="Base",
                latitude=19.076,
                longitude=72.877,
                radius_meters=100,
            ),
        )

        crud.store_gps_location(
            self.db,
            device_id=drone.id,
            latitude=19.0761,
            longitude=72.877,
        )

        self.assertEqual(crud.get_security_events(self.db), [])

    def test_create_geofence_evaluates_existing_drone_location(self):
        drone = self.create_device("Drone 1", models.DeviceType.drone)
        crud.store_gps_location(
            self.db,
            device_id=drone.id,
            latitude=19.086,
            longitude=72.877,
        )

        crud.create_geofence(
            self.db,
            schemas.GeofenceCreate(
                name="Base",
                latitude=19.076,
                longitude=72.877,
                radius_meters=100,
            ),
        )

        events = crud.get_security_events(self.db)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "geofence_exit")
        self.assertEqual(events[0].device_id, drone.id)

    def test_gps_updates_can_create_alert_every_minute(self):
        drone = self.create_device("Drone 1", models.DeviceType.drone)
        crud.create_geofence(
            self.db,
            schemas.GeofenceCreate(
                name="Base",
                latitude=19.076,
                longitude=72.877,
                radius_meters=100,
            ),
        )
        crud.store_gps_location(self.db, drone.id, 19.086, 72.877)
        first_event = crud.get_security_events(self.db)[0]
        first_event.created_at = datetime.now(timezone.utc) - timedelta(seconds=61)
        self.db.commit()

        crud.store_gps_location(self.db, drone.id, 19.0861, 72.877)

        self.assertEqual(len(crud.get_security_events(self.db)), 2)

    def test_stale_monitor_suppresses_alerts_for_five_minutes(self):
        drone = self.create_device("Drone 1", models.DeviceType.drone)
        crud.create_geofence(
            self.db,
            schemas.GeofenceCreate(
                name="Base",
                latitude=19.076,
                longitude=72.877,
                radius_meters=100,
            ),
        )
        crud.store_gps_location(self.db, drone.id, 19.086, 72.877)

        created_events = crud.evaluate_all_drone_geofences(
            self.db,
            cooldown_seconds=crud.STALE_GEOFENCE_ALERT_COOLDOWN_SECONDS
        )

        self.assertEqual(created_events, [])
        self.assertEqual(len(crud.get_security_events(self.db)), 1)


if __name__ == "__main__":
    unittest.main()
