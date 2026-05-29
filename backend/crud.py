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

def update_device_status(
    db,
    device_id,
    status
):
    device = get_device(db, device_id)

    if not device:
        return None

    device.status = status

    db.commit()
    db.refresh(device)

    return device

def update_device_status(db: Session, device_id: int, status: models.DeviceStatus):
    device = get_device(db, device_id)

    if not device:
        return None

    device.status = status
    db.commit()
    db.refresh(device)

    return device