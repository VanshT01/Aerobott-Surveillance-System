# control the api data
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from models import DeviceType, DeviceStatus


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