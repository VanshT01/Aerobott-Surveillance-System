# Backend Structure

The backend now uses a package layout under `backend/app`.

```text
backend/
├── app/
│   ├── main.py
│   ├── schemas.py
│   ├── db/
│   │   ├── session.py
│   │   └── models.py
│   ├── repositories/
│   │   └── crud.py
│   └── services/
│       ├── events/
│       │   └── detection_events.py
│       ├── telemetry/
│       │   └── mqtt.py
│       ├── video/
│       │   ├── recording.py
│       │   ├── rtsp.py
│       │   └── webrtc.py
│       └── vision/
│           ├── detection.py
│           ├── drone_crowd_counting.py
│           └── license_plate_detection.py
├── models/
│   ├── partBmodel_best.pth.tar
│   └── license_plate_detector.pt
```

## Dependency Direction

Keep dependencies flowing in this direction:

```text
main/router code -> services -> repositories -> db
```

Avoid importing FastAPI inside repositories or database models.

## Run Command

```bash
uvicorn app.main:app --app-dir backend
```

## Test Command

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Geofencing

Create circular geofences with:

```text
POST /geofences
GET /geofences
PATCH /geofences/{geofence_id}
DELETE /geofences/{geofence_id}
```

When drone GPS telemetry updates, the backend checks whether the drone is inside at least one geofence. If it is outside all configured geofences, it creates a `geofence_exit` security event. Recent alerts are available at:

```text
GET /security-events
```

Alert cadence:

```text
GPS updates while outside: at most once every 60 seconds
No GPS updates while outside: background watchdog re-alerts at most once every 5 minutes
```

## Drone Crowd Counting

The backend uses the CSRNet architecture from `leeyeehoo/CSRNet-pytorch` for
drone crowd counting. The deployed checkpoint lives at:

```text
backend/models/partBmodel_best.pth.tar
```

or set:

```bash
DRONE_CROWD_MODEL_PATH=/absolute/path/to/partBmodel_best.pth.tar
```

The dashboard will show the model as missing until that weights file exists.
The frontend status panel includes an `Estimate` button that captures one
frame from the selected camera/drone and returns the predicted crowd count.

To prepare the ShanghaiTech dataset and train a checkpoint:

```bash
python backend/scripts/prepare_shanghaitech_csrnet.py /path/to/ShanghaiTech
PYTHONPATH=backend python backend/scripts/train_csrnet_shanghaitech.py \
  --train-json backend/models/csrnet_data/part_A_train.json \
  --val-json backend/models/csrnet_data/part_A_test.json
```

Use `--no-vgg-pretrained` if the machine cannot download torchvision's VGG16
weights before training.

## License Plate Detection

The backend uses the YOLOv8 license plate detector from
`Mehak2005si/license-plate-detector-YOLOv8`. The runtime weight is stored at:

```text
backend/models/license_plate_detector.pt
```

Endpoints:

```text
GET /license-plate-detector/model/status
POST /devices/{device_id}/license-plates
POST /devices/{device_id}/license-plates?confidence=0.35
POST /devices/{device_id}/license-plates?read_text=true
```

The detector returns license plate bounding boxes by default. If
`read_text=true`, it also runs EasyOCR on each detected plate crop. EasyOCR
stores its downloaded OCR model files under `backend/models/easyocr/`.

Live streams and recordings do not run license plate OCR inline. When the
general object tracker detects a vehicle class (`car`, `truck`, `bus`, or
`motorcycle`), the event service queues a throttled background license-plate
scan on a snapshot. If a plate is found, the backend creates a normal event
such as:

```text
License plate 'MH12AB1234' detected
```

The frontend event feed picks this up through its existing `/events` polling
and shows the annotated snapshot with the plate box.
