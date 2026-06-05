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
│           └── drone_crowd_counting.py
├── models/
│   └── csrnet_drone.pth
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

## Drone Crowd Counting

The backend uses a CSRNet model for drone crowd counting.
Place trained weights at:

```text
backend/models/csrnet_drone.pth
```

or set:

```bash
DRONE_CROWD_MODEL_PATH=/absolute/path/to/csrnet_drone.pth
```

The dashboard will show the model as missing until that weights file exists.
