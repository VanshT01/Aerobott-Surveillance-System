# handles the database actions
import json
import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import models
from app import schemas
from app.services.notifications import webhooks


EARTH_RADIUS_METERS = 6371000
GPS_GEOFENCE_ALERT_COOLDOWN_SECONDS = 60
STALE_GEOFENCE_ALERT_COOLDOWN_SECONDS = 300


def distance_meters(lat1: float, lon1: float, lat2: float, lon2: float):
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_METERS * c


def create_device(db: Session, device: schemas.DeviceCreate):
    db_device = models.Device(**device.model_dump())
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device


def get_devices(db: Session):
    return db.query(models.Device).all()


def get_device(db: Session, device_id: int):
    return db.query(models.Device).filter(models.Device.id == device_id).first()


def update_device(db: Session, device_id: int, device_update: schemas.DeviceUpdate):
    db_device = get_device(db, device_id)

    if not db_device:
        return None

    update_data = device_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_device, key, value)

    db.commit()
    db.refresh(db_device)

    return db_device


def delete_device(db: Session, device_id: int):
    db_device = get_device(db, device_id)

    if not db_device:
        return None

    db.query(models.CameraCredentials).filter(
        models.CameraCredentials.device_id == device_id
    ).delete()
    db.query(models.Recording).filter(
        models.Recording.camera_id == device_id
    ).delete()
    db.query(models.Event).filter(
        models.Event.camera_id == device_id
    ).delete()
    db.query(models.PersonAppearance).filter(
        models.PersonAppearance.camera_id == device_id
    ).delete()
    db.query(models.GPSLocation).filter(
        models.GPSLocation.device_id == device_id
    ).delete()
    db.query(models.SecurityEvent).filter(
        models.SecurityEvent.device_id == device_id
    ).delete()

    db.delete(db_device)
    db.commit()

    return db_device

def create_camera_credentials(db: Session, credentials: schemas.CameraCredentialsCreate):
    db_credentials = models.CameraCredentials(**credentials.model_dump())

    db.add(db_credentials)
    db.commit()
    db.refresh(db_credentials)

    return db_credentials


def get_camera_credentials(db: Session, device_id: int):
    return (
        db.query(models.CameraCredentials)
        .filter(models.CameraCredentials.device_id == device_id)
        .first()
    )

def update_device_status(db: Session, device_id: int, status: models.DeviceStatus):
    device = get_device(db, device_id)

    if not device:
        return None

    device.status = status
    db.commit()
    db.refresh(device)

    return device

def create_recording(db: Session, camera_id: int, start_time, end_time, path: str):
    recording = models.Recording(
        camera_id=camera_id,
        start_time=start_time,
        end_time=end_time,
        path=path
    )

    db.add(recording)
    db.commit()
    db.refresh(recording)

    return recording


def get_recordings(db: Session, camera_id: int | None = None):
    query = db.query(models.Recording)

    if camera_id is not None:
        query = query.filter(models.Recording.camera_id == camera_id)

    return query.order_by(models.Recording.start_time.desc()).all()

def delete_recordings(db: Session, camera_id: int | None = None):
    query = db.query(models.Recording)

    if camera_id is not None:
        query = query.filter(models.Recording.camera_id == camera_id)

    count = query.count()
    query.delete()
    db.commit()

    return count


def create_event(db: Session, camera_id: int, event_type: str, event_time, snapshot: str):
    event = models.Event(
        camera_id=camera_id,
        type=event_type,
        time=event_time,
        snapshot=snapshot
    )

    db.add(event)
    db.commit()
    db.refresh(event)
    webhooks.notify_event(event)

    return event


def get_events(db: Session, camera_id: int | None = None, limit: int = 50):
    query = db.query(models.Event)

    if camera_id is not None:
        query = query.filter(models.Event.camera_id == camera_id)

    return query.order_by(models.Event.time.desc()).limit(limit).all()


def delete_events(db: Session, camera_id: int | None = None):
    query = db.query(models.Event)

    if camera_id is not None:
        query = query.filter(models.Event.camera_id == camera_id)

    count = query.count()
    query.delete()
    db.commit()

    return count


def get_event(db: Session, event_id: int):
    return db.query(models.Event).filter(models.Event.id == event_id).first()


def _encode_json(value):
    return json.dumps(value, separators=(",", ":"))


def _decode_json(value):
    return json.loads(value)


def get_person_identity(db: Session, identity_id: int):
    return (
        db.query(models.PersonIdentity)
        .filter(models.PersonIdentity.id == identity_id)
        .first()
    )


def get_person_identities(db: Session, limit: int = 50):
    last_seen = (
        db.query(
            models.PersonAppearance.identity_id,
            func.max(models.PersonAppearance.time).label("last_seen")
        )
        .group_by(models.PersonAppearance.identity_id)
        .subquery()
    )

    rows = (
        db.query(models.PersonIdentity, last_seen.c.last_seen)
        .outerjoin(last_seen, models.PersonIdentity.id == last_seen.c.identity_id)
        .order_by(last_seen.c.last_seen.desc().nullslast(), models.PersonIdentity.id.desc())
        .limit(limit)
        .all()
    )

    return rows


def get_identity_embeddings(db: Session):
    return db.query(models.PersonIdentity).all()


def create_person_identity(db: Session, embedding: list[float]):
    identity = models.PersonIdentity(
        label="pending",
        centroid_embedding=_encode_json(embedding),
        appearance_count=0
    )

    db.add(identity)
    db.flush()
    identity.label = f"Person {identity.id}"
    db.commit()
    db.refresh(identity)

    return identity


def update_person_identity_centroid(
    db: Session,
    identity: models.PersonIdentity,
    embedding: list[float]
):
    count = max(0, identity.appearance_count)
    current = _decode_json(identity.centroid_embedding)

    if count == 0:
        next_centroid = embedding
    else:
        next_centroid = [
            ((current_value * count) + embedding_value) / (count + 1)
            for current_value, embedding_value in zip(current, embedding)
        ]

    identity.centroid_embedding = _encode_json(next_centroid)
    identity.appearance_count = count + 1
    db.commit()
    db.refresh(identity)

    return identity


def create_person_appearance(
    db: Session,
    identity_id: int,
    camera_id: int,
    tracking_id: int | None,
    event_time: datetime,
    snapshot: str,
    bbox: list[int],
    embedding: list[float],
    similarity: float | None
):
    appearance = models.PersonAppearance(
        identity_id=identity_id,
        camera_id=camera_id,
        tracking_id=tracking_id,
        time=event_time,
        snapshot=snapshot,
        bbox=_encode_json(bbox),
        embedding=_encode_json(embedding),
        similarity=similarity
    )

    db.add(appearance)
    db.commit()
    db.refresh(appearance)

    return appearance


def get_person_appearances(
    db: Session,
    identity_id: int | None = None,
    camera_id: int | None = None,
    since: datetime | None = None,
    limit: int = 100
):
    query = db.query(models.PersonAppearance)

    if identity_id is not None:
        query = query.filter(models.PersonAppearance.identity_id == identity_id)

    if camera_id is not None:
        query = query.filter(models.PersonAppearance.camera_id == camera_id)

    if since is not None:
        query = query.filter(models.PersonAppearance.time >= since)

    return query.order_by(models.PersonAppearance.time.desc()).limit(limit).all()


def person_appearance_to_response(appearance: models.PersonAppearance):
    return {
        "id": appearance.id,
        "identity_id": appearance.identity_id,
        "camera_id": appearance.camera_id,
        "tracking_id": appearance.tracking_id,
        "time": appearance.time,
        "snapshot": appearance.snapshot,
        "bbox": _decode_json(appearance.bbox),
        "similarity": appearance.similarity
    }


def delete_reid_data(db: Session):
    appearance_count = db.query(models.PersonAppearance).count()
    identity_count = db.query(models.PersonIdentity).count()
    db.query(models.PersonAppearance).delete()
    db.query(models.PersonIdentity).delete()
    db.commit()

    return {
        "deleted_identities": identity_count,
        "deleted_appearances": appearance_count
    }


def store_gps_location(db: Session, device_id: int, latitude: float, longitude: float):
    device = get_device(db, device_id)

    if not device:
        return None

    if device.device_type != models.DeviceType.drone:
        return None

    device.latitude = str(latitude)
    device.longitude = str(longitude)
    device.status = models.DeviceStatus.online

    location = models.GPSLocation(
        device_id=device_id,
        latitude=latitude,
        longitude=longitude
    )

    db.add(location)
    db.commit()
    db.refresh(location)
    evaluate_geofence_exit(db, device, latitude, longitude)

    return location


def get_gps_locations(db: Session, device_id: int | None = None, limit: int = 100):
    query = db.query(models.GPSLocation)

    if device_id is not None:
        query = query.filter(models.GPSLocation.device_id == device_id)

    return query.order_by(models.GPSLocation.created_at.desc()).limit(limit).all()


def create_geofence(db: Session, geofence: schemas.GeofenceCreate):
    db_geofence = models.Geofence(**geofence.model_dump())
    db.add(db_geofence)
    db.commit()
    db.refresh(db_geofence)
    evaluate_all_drone_geofences(db)
    return db_geofence


def get_geofences(db: Session):
    return db.query(models.Geofence).order_by(models.Geofence.name.asc()).all()


def get_geofence(db: Session, geofence_id: int):
    return db.query(models.Geofence).filter(models.Geofence.id == geofence_id).first()


def update_geofence(db: Session, geofence_id: int, geofence_update: schemas.GeofenceUpdate):
    geofence = get_geofence(db, geofence_id)

    if not geofence:
        return None

    update_data = geofence_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(geofence, key, value)

    db.commit()
    db.refresh(geofence)
    evaluate_all_drone_geofences(db)

    return geofence


def delete_geofence(db: Session, geofence_id: int):
    geofence = get_geofence(db, geofence_id)

    if not geofence:
        return None

    db.query(models.SecurityEvent).filter(
        models.SecurityEvent.geofence_id == geofence_id
    ).delete()
    db.delete(geofence)
    db.commit()

    return geofence


def get_security_events(
    db: Session,
    device_id: int | None = None,
    limit: int = 50
):
    query = db.query(models.SecurityEvent)

    if device_id is not None:
        query = query.filter(models.SecurityEvent.device_id == device_id)

    return query.order_by(models.SecurityEvent.created_at.desc()).limit(limit).all()


def delete_security_events(db: Session, device_id: int | None = None):
    query = db.query(models.SecurityEvent)

    if device_id is not None:
        query = query.filter(models.SecurityEvent.device_id == device_id)

    count = query.count()
    query.delete()
    db.commit()

    return count


def create_security_event(
    db: Session,
    event_type: str,
    device_id: int,
    geofence_id: int | None,
    latitude: float,
    longitude: float,
    message: str
):
    event = models.SecurityEvent(
        event_type=event_type,
        device_id=device_id,
        geofence_id=geofence_id,
        latitude=latitude,
        longitude=longitude,
        message=message
    )

    db.add(event)
    db.commit()
    db.refresh(event)
    webhooks.notify_security_alert(event)

    return event


def get_recent_security_event(
    db: Session,
    event_type: str,
    device_id: int,
    geofence_id: int | None,
    cooldown_seconds: int = GPS_GEOFENCE_ALERT_COOLDOWN_SECONDS
):
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=cooldown_seconds)
    query = (
        db.query(models.SecurityEvent)
        .filter(models.SecurityEvent.event_type == event_type)
        .filter(models.SecurityEvent.device_id == device_id)
        .filter(models.SecurityEvent.created_at >= cutoff)
    )

    if geofence_id is None:
        query = query.filter(models.SecurityEvent.geofence_id.is_(None))
    else:
        query = query.filter(models.SecurityEvent.geofence_id == geofence_id)

    return query.order_by(models.SecurityEvent.created_at.desc()).first()


def evaluate_geofence_exit(
    db: Session,
    device,
    latitude: float,
    longitude: float,
    cooldown_seconds: int = GPS_GEOFENCE_ALERT_COOLDOWN_SECONDS
):
    geofences = get_geofences(db)

    if not geofences:
        return []

    created_events = []

    for geofence in geofences:
        distance = distance_meters(
            latitude,
            longitude,
            geofence.latitude,
            geofence.longitude
        )

        if distance <= geofence.radius_meters:
            continue

        event_type = "geofence_exit"

        recent_event = get_recent_security_event(
            db=db,
            event_type=event_type,
            device_id=device.id,
            geofence_id=geofence.id,
            cooldown_seconds=cooldown_seconds
        )

        if recent_event:
            continue

        outside_by = max(0, distance - geofence.radius_meters)
        message = (
            f"{device.name} is outside geofence {geofence.name} "
            f"by {outside_by:.1f} meters"
        )

        created_events.append(
            create_security_event(
                db=db,
                event_type=event_type,
                device_id=device.id,
                geofence_id=geofence.id,
                latitude=latitude,
                longitude=longitude,
                message=message
            )
        )

    return created_events


def evaluate_all_drone_geofences(
    db: Session,
    cooldown_seconds: int = STALE_GEOFENCE_ALERT_COOLDOWN_SECONDS
):
    drones = (
        db.query(models.Device)
        .filter(models.Device.device_type == models.DeviceType.drone)
        .filter(models.Device.latitude.isnot(None))
        .filter(models.Device.longitude.isnot(None))
        .all()
    )

    created_events = []

    for drone in drones:
        try:
            latitude = float(drone.latitude)
            longitude = float(drone.longitude)
        except (TypeError, ValueError):
            continue

        events = evaluate_geofence_exit(
            db=db,
            device=drone,
            latitude=latitude,
            longitude=longitude,
            cooldown_seconds=cooldown_seconds
        )

        created_events.extend(events)

    return created_events
