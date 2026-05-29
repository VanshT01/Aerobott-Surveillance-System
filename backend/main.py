from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
import threading
from rtsp_service import (
    monitor_cameras,
    check_rtsp_stream,
    get_stream_info,
    generate_mjpeg_stream
)
import models
from models import DeviceStatus
import schemas
import crud
from database import engine, get_db
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiortc import RTCPeerConnection, RTCSessionDescription
from webrtc_service import CameraVideoTrack
from recording_service import start_recording, stop_recording, is_recording
import os

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Surveillance System API",
    description="Phase 1: Device registration service",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
pcs = set()

class WebRTCOffer(BaseModel):
    sdp: str
    type: str


@app.get("/")
def root():
    return {"message": "Surveillance System Backend Running"}


@app.post("/devices", response_model=schemas.DeviceResponse)
def create_device(device: schemas.DeviceCreate, db: Session = Depends(get_db)):
    return crud.create_device(db, device)


@app.get("/devices", response_model=list[schemas.DeviceResponse])
def get_devices(db: Session = Depends(get_db)):
    return crud.get_devices(db)


@app.get("/devices/{device_id}", response_model=schemas.DeviceResponse)
def get_device(device_id: int, db: Session = Depends(get_db)):
    device = crud.get_device(db, device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return device


@app.patch("/devices/{device_id}", response_model=schemas.DeviceResponse)
def update_device(
    device_id: int,
    device_update: schemas.DeviceUpdate,
    db: Session = Depends(get_db)
):
    device = crud.update_device(db, device_id, device_update)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return device


@app.delete("/devices/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = crud.delete_device(db, device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return {"message": "Device deleted successfully"}

@app.post("/camera-credentials", response_model=schemas.CameraCredentialsResponse)
def create_camera_credentials(
    credentials: schemas.CameraCredentialsCreate,
    db: Session = Depends(get_db)
):
    device = crud.get_device(db, credentials.device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    existing_credentials = crud.get_camera_credentials(db, credentials.device_id)

    if existing_credentials:
        raise HTTPException(
            status_code=400,
            detail="Credentials already exist for this device"
        )

    return crud.create_camera_credentials(db, credentials)


@app.get("/camera-credentials/{device_id}", response_model=schemas.CameraCredentialsResponse)
def get_camera_credentials(device_id: int, db: Session = Depends(get_db)):
    credentials = crud.get_camera_credentials(db, device_id)

    if not credentials:
        raise HTTPException(status_code=404, detail="Credentials not found")

    return credentials

@app.on_event("startup")
def startup_event():

    monitor_thread = threading.Thread(
        target=monitor_cameras,
        daemon=True
    )

    monitor_thread.start()

@app.post("/devices/{device_id}/check-stream", response_model=schemas.DeviceResponse)
def check_device_stream(device_id: int, db: Session = Depends(get_db)):
    device = crud.get_device(db, device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if device.device_type != models.DeviceType.camera:
        raise HTTPException(status_code=400, detail="Device is not a camera")

    if not device.rtsp_url:
        raise HTTPException(status_code=400, detail="Camera does not have an RTSP URL")

    online = check_rtsp_stream(device.rtsp_url)

    new_status = DeviceStatus.online if online else DeviceStatus.offline

    updated_device = crud.update_device_status(db, device_id, new_status)

    return updated_device

@app.get("/devices/{device_id}/stream-info")
def get_device_stream_info(device_id: int, db: Session = Depends(get_db)):
    device = crud.get_device(db, device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if device.device_type != models.DeviceType.camera:
        raise HTTPException(status_code=400, detail="Device is not a camera")

    if not device.rtsp_url:
        raise HTTPException(status_code=400, detail="Camera does not have an RTSP URL")

    info = get_stream_info(device.rtsp_url)

    return {
        "device_id": device.id,
        "name": device.name,
        "rtsp_url": device.rtsp_url,
        "stream_info": info
    }

@app.get("/devices/{device_id}/live")
def live_view(device_id: int, db: Session = Depends(get_db)):
    device = crud.get_device(db, device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if device.device_type != models.DeviceType.camera:
        raise HTTPException(status_code=400, detail="Device is not a camera")

    if not device.rtsp_url:
        raise HTTPException(status_code=400, detail="Camera does not have an RTSP URL")

    return StreamingResponse(
        generate_mjpeg_stream(device.rtsp_url),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/devices/{device_id}/dashboard")
def camera_dashboard(device_id: int, db: Session = Depends(get_db)):
    device = crud.get_device(db, device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    info = get_stream_info(device.rtsp_url)

    resolution = "Unavailable"

    if info["width"] and info["height"]:
        resolution = f"{int(info['width'])}x{int(info['height'])}"

    return {
        "device_id": device.id,
        "name": device.name,
        "status": device.status,
        "resolution": resolution,
        "fps": info["fps"],
        "last_updated": device.updated_at
    }

@app.post("/devices/{device_id}/webrtc")
async def webrtc_offer(device_id: int, offer: WebRTCOffer, db: Session = Depends(get_db)):
    device = crud.get_device(db, device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if device.device_type != models.DeviceType.camera:
        raise HTTPException(status_code=400, detail="Device is not a camera")

    if not device.rtsp_url:
        raise HTTPException(status_code=400, detail="Camera does not have an RTSP URL")

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print("WebRTC connection state:", pc.connectionState)

        if pc.connectionState in ["failed", "closed", "disconnected"]:
            await pc.close()
            pcs.discard(pc)

    video_track = CameraVideoTrack(device.rtsp_url)
    pc.addTrack(video_track)

    rtc_offer = RTCSessionDescription(
        sdp=offer.sdp,
        type=offer.type
    )

    await pc.setRemoteDescription(rtc_offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return {
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    }

@app.post("/devices/{device_id}/recording/start")
def start_device_recording(device_id: int, db: Session = Depends(get_db)):
    device = crud.get_device(db, device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if device.device_type != models.DeviceType.camera:
        raise HTTPException(status_code=400, detail="Device is not a camera")

    if not device.rtsp_url:
        raise HTTPException(status_code=400, detail="Camera does not have an RTSP URL")

    started = start_recording(device.id, device.rtsp_url)

    if not started:
        return {
            "message": "Recording already running",
            "camera_id": device.id
        }

    return {
        "message": "Recording started",
        "camera_id": device.id
    }


@app.post("/devices/{device_id}/recording/stop")
def stop_device_recording(device_id: int):
    stopped = stop_recording(device_id)

    if not stopped:
        return {
            "message": "Recording was not running",
            "camera_id": device_id
        }

    return {
        "message": "Recording stopped",
        "camera_id": device_id
    }


@app.get("/devices/{device_id}/recording/status")
def get_recording_status(device_id: int):
    return {
        "camera_id": device_id,
        "recording": is_recording(device_id)
    }

@app.get("/recordings/{recording_id}/download")
def download_recording(recording_id: int, db: Session = Depends(get_db)):
    recording = (
        db.query(models.Recording)
        .filter(models.Recording.id == recording_id)
        .first()
    )

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    if not os.path.exists(recording.path):
        raise HTTPException(status_code=404, detail="Recording file missing")

    return FileResponse(
        recording.path,
        media_type="video/mp4",
        filename=os.path.basename(recording.path)
    )

@app.delete("/recordings")
def delete_recordings(camera_id: int | None = None, db: Session = Depends(get_db)):
    deleted_count = crud.delete_recordings(db, camera_id)

    return {
        "message": "Recording metadata deleted",
        "deleted_count": deleted_count
    }