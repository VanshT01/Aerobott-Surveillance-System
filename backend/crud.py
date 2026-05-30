# handles the database actions
from sqlalchemy.orm import Session

import models
import schemas


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

    return event


def get_events(db: Session, camera_id: int | None = None, limit: int = 50):
    query = db.query(models.Event)

    if camera_id is not None:
        query = query.filter(models.Event.camera_id == camera_id)

    return query.order_by(models.Event.time.desc()).limit(limit).all()


def get_event(db: Session, event_id: int):
    return db.query(models.Event).filter(models.Event.id == event_id).first()
