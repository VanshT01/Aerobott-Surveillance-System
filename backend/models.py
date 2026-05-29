# create the devices table
from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
import enum

from database import Base


class DeviceType(str, enum.Enum):
    camera = "camera"
    gps_tracker = "gps_tracker"
    drone = "drone"


class DeviceStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    unknown = "unknown"


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    device_type = Column(Enum(DeviceType), nullable=False)

    ip_address = Column(String, nullable=True)
    rtsp_url = Column(String, nullable=True)
    onvif_url = Column(String, nullable=True)

    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)

    status = Column(Enum(DeviceStatus), default=DeviceStatus.unknown)

    location_name = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class CameraCredentials(Base):
    __tablename__ = "camera_credentials"

    id = Column(Integer, primary_key=True, index=True)

    # One credentials record per camera
    device_id = Column(Integer, nullable=False, unique=True)

    username = Column(String, nullable=True)
    password = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now()
    )

# for camera:
# name
# device_type
# ip_address
# rtsp_url
# onvif_url
# location_name

# for gps tracker:
# latitude
# longitude
# status

# for future drone can reuse:
# rtsp_url
# latitude
# longitude
# status