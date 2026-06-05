import json
import os
import sys
import unittest
from datetime import datetime, timezone
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


if __name__ == "__main__":
    unittest.main()
