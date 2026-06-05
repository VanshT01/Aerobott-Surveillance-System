import time

from app.db.session import SessionLocal
from app.repositories import crud


GEOFENCE_MONITOR_INTERVAL_SECONDS = 60


def monitor_geofence_alerts():
    while True:
        db = SessionLocal()

        try:
            created_events = crud.evaluate_all_drone_geofences(
                db,
                cooldown_seconds=crud.STALE_GEOFENCE_ALERT_COOLDOWN_SECONDS
            )

            if created_events:
                print(f"Created {len(created_events)} stale geofence alert(s)")
        finally:
            db.close()

        time.sleep(GEOFENCE_MONITOR_INTERVAL_SECONDS)
