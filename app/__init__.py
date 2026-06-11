from pathlib import Path


BACKEND_APP = Path(__file__).resolve().parents[1] / "backend" / "app"

if BACKEND_APP.exists():
    __path__.append(str(BACKEND_APP))
