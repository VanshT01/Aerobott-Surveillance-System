# control the api data
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.db.models import DeviceType, DeviceStatus


class DeviceCreate(BaseModel):  # used when adding a device
    name: str
    device_type: DeviceType

    ip_address: Optional[str] = None
    rtsp_url: Optional[str] = None
    onvif_url: Optional[str] = None

    latitude: Optional[str] = None
    longitude: Optional[str] = None

    location_name: Optional[str] = None


class DeviceUpdate(BaseModel):  # used when editing a device
    name: Optional[str] = None
    ip_address: Optional[str] = None
    rtsp_url: Optional[str] = None
    onvif_url: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    location_name: Optional[str] = None
    status: Optional[DeviceStatus] = None


class DeviceResponse(BaseModel):    # what the backend sends back
    id: int
    name: str
    device_type: DeviceType

    ip_address: Optional[str]
    rtsp_url: Optional[str]
    onvif_url: Optional[str]

    latitude: Optional[str]
    longitude: Optional[str]

    status: DeviceStatus
    location_name: Optional[str]

    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class CameraCredentialsCreate(BaseModel):
    device_id: int
    username: Optional[str] = None
    password: Optional[str] = None


class CameraCredentialsResponse(BaseModel):
    id: int
    device_id: int
    username: Optional[str]
    password: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RecordingResponse(BaseModel):
    id: int
    camera_id: int
    start_time: datetime
    end_time: datetime
    path: str
    created_at: datetime

    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    id: int
    camera_id: int
    type: str
    time: datetime
    snapshot: str

    class Config:
        from_attributes = True


class PersonIdentityResponse(BaseModel):
    id: int
    label: str
    appearance_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    last_seen: Optional[datetime] = None

    class Config:
        from_attributes = True


class PersonAppearanceResponse(BaseModel):
    id: int
    identity_id: int
    camera_id: int
    tracking_id: Optional[int]
    time: datetime
    snapshot: str
    bbox: list[int]
    similarity: Optional[float]


class GPSLocationCreate(BaseModel):
    device_id: int
    latitude: float
    longitude: float


class GPSLocationResponse(BaseModel):
    id: int
    device_id: int
    latitude: float
    longitude: float
    created_at: datetime

    class Config:
        from_attributes = True


class DroneCrowdCountResponse(BaseModel):
    device_id: int
    count: float
    model_name: str
    model_path: str
    runtime_device: str


class LicensePlateDetection(BaseModel):
    class_: str = Field(alias="class")
    confidence: float
    box: list[int]
    text: Optional[str] = None

    class Config:
        populate_by_name = True


class LicensePlateDetectionResponse(BaseModel):
    device_id: int
    detections: list[LicensePlateDetection]
    model_name: str
    model_path: str
    runtime_device: str


class GeofenceCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    radius_meters: float


class GeofenceUpdate(BaseModel):
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_meters: Optional[float] = None


class GeofenceResponse(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    radius_meters: float
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class SecurityEventResponse(BaseModel):
    id: int
    event_type: str
    device_id: int
    geofence_id: Optional[int]
    latitude: float
    longitude: float
    message: str
    created_at: datetime

    class Config:
        from_attributes = True
