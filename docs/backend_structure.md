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
│           ├── crowd_counting.py
│           └── detection.py
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
